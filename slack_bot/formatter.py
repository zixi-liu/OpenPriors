"""Format extraction results as Slack Block Kit messages."""

from typing import Dict, Any, List


def format_extraction_blocks(result: Dict[str, Any]) -> List[Dict]:
    """Turn a pipeline result into Slack Block Kit blocks."""
    blocks = []
    title = result.get("title", "Untitled")
    summary = result.get("summary", "")
    priors = result.get("priors", [])
    quotes = result.get("notable_quotes", [])

    # Header
    blocks.append({
        "type": "header",
        "text": {"type": "plain_text", "text": _truncate(title, 150), "emoji": True}
    })

    # Summary
    if summary:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": summary[:3000]}
        })

    # Quotes
    if quotes:
        quotes_text = "\n".join(f'> _{_truncate(q, 200)}_' for q in quotes[:5])
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Notable Quotes*\n{quotes_text}"}
        })

    # Priors
    if priors:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{len(priors)} Priors Extracted*"}
        })
        for p in priors[:10]:
            prior_text = f"*{p.get('name', '')}*\n{p.get('principle', '')}\n_Practice:_ {p.get('practice', '')}"
            if p.get("quote"):
                prior_text += f"\n> _{_truncate(p['quote'], 150)}_"
            blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": _truncate(prior_text, 3000)}
            })

        if len(priors) > 10:
            blocks.append({
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": f"_{len(priors) - 10} more priors saved_"}]
            })

    # Footer
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Saved to OpenPriors · {len(priors)} priors extracted"}]
    })

    # Slack limit: max 50 blocks
    return blocks[:50]


def format_fallback_text(result: Dict[str, Any]) -> str:
    """Plain text fallback for notifications."""
    title = result.get("title", "Untitled")
    count = result.get("priors_count", 0)
    return f"Extracted {count} priors from {title}"


def _truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."
