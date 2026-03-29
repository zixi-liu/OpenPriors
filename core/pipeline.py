"""
Shared extraction pipeline.

Used by both the web routes and the Slack bot to avoid duplicating logic.
"""

from typing import Dict, Any

from core.extractor import extract_from_url, extract_priors, format_for_display
from core.storage import save_material, save_priors


async def process_url(url: str, session_id: str = "") -> Dict[str, Any]:
    """
    Full pipeline: fetch URL → extract priors → save material + priors.
    Returns a result dict with everything needed for display.
    """
    extracted = await extract_from_url(url)
    content = extracted.get("content", "")
    if not content:
        return {"success": False, "error": "Could not extract content from URL"}

    result = await extract_priors(content, source_hint=url)
    title = extracted.get("title", "") or result.get("title", "")
    is_youtube = "youtu" in url
    detected_type = result.get("source_type", "other")

    # Decide what to store
    if is_youtube:
        stored_content = content
    elif detected_type in ("book", "movie"):
        notable_quotes = result.get("notable_quotes", [])
        quotes_section = "\n".join(f'"{q}"' for q in notable_quotes) if notable_quotes else ""
        stored_content = f"{result.get('summary', '')}\n\n{quotes_section}".strip()
    else:
        stored_content = content

    formatted_content = await format_for_display(stored_content)
    material_id = save_material(
        title=title,
        content=formatted_content,
        source_type="youtube" if is_youtube else "url",
        url=url,
        summary=result.get("summary", ""),
        author=extracted.get("author", ""),
        session_id=session_id,
    )
    priors = result.get("priors", [])
    ids = save_priors(priors, source_title=title, material_id=material_id)

    return {
        "success": True,
        "title": title,
        "summary": result.get("summary", ""),
        "source_type": detected_type,
        "notable_quotes": result.get("notable_quotes", []),
        "priors_count": len(ids),
        "priors": priors,
        "ids": ids,
        "material_id": material_id,
    }
