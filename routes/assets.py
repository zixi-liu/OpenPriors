"""
Assets Routes

An asset is a learning material — either uploaded (PDF, URL) or captured via voice Q&A.
Both produce the same result: extracted priors stored locally.
"""

import base64
import time

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from core.llm import complete, complete_json, parse_json
from core.extractor import extract_priors, extract_from_url, format_for_display
from core.storage import save_priors, save_material, get_material, get_all_materials, delete_material, get_all_priors, search_priors, get_prior
from core.embeddings import index_material, index_prior, hybrid_search

router = APIRouter(prefix="/api/assets", tags=["assets"])


async def _embed_material_and_priors(material_id: str, content: str, priors: list, title: str):
    """Background: embed material chunks + individual priors."""
    try:
        await index_material(material_id, content)
        for prior in priors:
            await index_prior(
                prior_id=prior.get("name", ""),
                material_id=material_id,
                principle=prior.get("principle", ""),
                practice=prior.get("practice", ""),
                source=prior.get("source", title),
            )
    except Exception as e:
        print(f"Embedding failed (non-blocking): {e}")


# ============================================================
# Upload (PDF, URL, text)
# ============================================================

class UploadTextRequest(BaseModel):
    content: str
    source: Optional[str] = None
    session_id: Optional[str] = None


class UploadURLRequest(BaseModel):
    url: str
    session_id: Optional[str] = None


@router.post("/upload/text")
async def upload_text(request: UploadTextRequest):
    try:
        result = await extract_priors(request.content, source_hint=request.source or "")
        title = result.get("title", request.source or "Untitled")
        formatted = await format_for_display(request.content)
        material_id = save_material(
            title=title,
            content=formatted,
            source_type="text",
            summary=result.get("summary", ""),
            session_id=request.session_id or "",
        )
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=title, material_id=material_id)
        await _embed_material_and_priors(material_id, request.content, priors, title)
        return JSONResponse({
            "success": True,
            "title": title,
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
            "material_id": material_id,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/upload/url")
async def upload_url(request: UploadURLRequest):
    try:
        from core.pipeline import process_url
        result = await process_url(request.url, session_id=request.session_id or "")
        if not result.get("success"):
            return JSONResponse({"success": False, "error": result.get("error", "Unknown error")})
        # Embed in background
        await _embed_material_and_priors(
            result["material_id"], "", result["priors"], result["title"]
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        result = await extract_priors(text, source_hint=file.filename or "uploaded PDF")
        title = result.get("title", file.filename or "Uploaded PDF")
        material_id = save_material(
            title=title,
            content=text,
            source_type="pdf",
            summary=result.get("summary", ""),
        )
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=title, material_id=material_id)
        await _embed_material_and_priors(material_id, text, priors, title)
        return JSONResponse({
            "success": True,
            "title": title,
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
            "material_id": material_id,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================
# Voice Q&A (same architecture as coach-ai story.py)
# ============================================================

class QAPair(BaseModel):
    question: str
    answer: str


class NextQuestionRequest(BaseModel):
    conversation: List[QAPair]


class NextQuestionResponse(BaseModel):
    question: str
    isComplete: bool


@router.post("/voice/next-question", response_model=NextQuestionResponse)
async def voice_next_question(req: NextQuestionRequest):
    round_num = len(req.conversation)

    conversation_so_far = ""
    for qa in req.conversation:
        conversation_so_far += f"Q: {qa.question}\nA: {qa.answer}\n\n"

    if round_num == 0:
        round_guidance = """This is the FIRST question. Ask what they learned recently that shifted their thinking.
Examples of good openers: "What's something you read, watched, or heard recently that changed how you think?", "What's an idea you encountered lately that stuck with you?"
Do NOT ask about specifics yet. Just get them talking about what they learned."""
    elif round_num == 1:
        round_guidance = """This is round 2. Based on what they shared, ask where this shows up or is missing in their actual life. Keep it conversational and short."""
    else:
        round_guidance = """This is the last round. Ask what one small thing they'll do differently this week. Keep it short."""

    system_prompt = f"""You are a warm, curious learning coach helping someone reflect on what they recently learned.

{round_guidance}

Previous conversation:
{conversation_so_far}

Rules:
- Ask exactly ONE question
- Keep it short and conversational (1 sentence, 2 max)
- Match their energy — if they're brief, keep it light; if they're detailed, dig deeper
- After 3 rounds, respond with EXACTLY: "COMPLETE"
- Never sound like a formal interview"""

    response = await complete(
        prompt="Generate the next question.",
        system_message=system_prompt,
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=150,
    )

    text = response.content.strip()

    if "COMPLETE" in text or round_num >= 3:
        return NextQuestionResponse(question="", isComplete=True)

    return NextQuestionResponse(question=text, isComplete=False)


class GenerateRequest(BaseModel):
    conversation: List[QAPair]


COMPILE_LEARNING_PROMPT = """You are helping someone organize their thoughts about something they recently learned.

They just had a casual voice conversation answering a few questions. The transcript below may have speech-to-text errors — use context to infer what they likely meant.

Raw Q&A transcript:
---
{conversation}
---

Rewrite this into a clear, first-person learning reflection (150-400 words) that:
1. Focuses on WHAT they learned and WHY it matters to them
2. Captures any specific sources they mentioned (book titles, movies, podcasts, articles, people)
3. Includes their personal reflections and how it connects to their life
4. Fixes any obvious speech-to-text errors (e.g. "atomic habits" not "a tomic have its")
5. Preserves their voice and tone — don't make it formal, keep it natural
6. Organizes scattered thoughts into a coherent narrative

Return JSON:
{{
  "title": "short title (3-6 words)",
  "reflection": "the rewritten learning reflection",
  "sources_mentioned": ["list of any books, movies, podcasts, articles, or people mentioned"]
}}

Return ONLY valid JSON."""


@router.post("/voice/generate")
async def voice_generate(req: GenerateRequest):
    """Compile voice Q&A into a learning reflection, save as material, then extract priors."""
    try:
        raw_conversation = "\n\n".join([
            f"Q: {qa.question}\nA: {qa.answer}"
            for qa in req.conversation
        ])

        # Step 1: Reorganize into a coherent learning reflection
        compiled = await complete_json(
            COMPILE_LEARNING_PROMPT.format(conversation=raw_conversation)
        )
        reflection = compiled.get("reflection", raw_conversation)
        title = compiled.get("title", "Voice Reflection")
        sources = compiled.get("sources_mentioned", [])
        source_hint = ", ".join(sources) if sources else "voice reflection"

        # Step 2: Save the compiled reflection as a material
        material_id = save_material(
            title=title,
            content=reflection,
            source_type="voice",
            summary=f"Sources: {source_hint}" if sources else "",
        )

        # Step 3: Extract priors from the clean reflection
        result = await extract_priors(reflection, source_hint=source_hint)
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=title, material_id=material_id)
        await _embed_material_and_priors(material_id, reflection, priors, title)

        return JSONResponse({
            "success": True,
            "title": title,
            "summary": result.get("summary", ""),
            "reflection": reflection,
            "sources_mentioned": sources,
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
            "material_id": material_id,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ============================================================
# Materials
# ============================================================

@router.get("/materials")
async def list_materials():
    materials = get_all_materials()
    # Return without full content for the list view
    return JSONResponse({
        "success": True,
        "materials": [
            {k: v for k, v in m.items() if k != "content"}
            for m in materials
        ],
        "count": len(materials),
    })


@router.get("/materials/{material_id}")
async def get_material_detail(material_id: str):
    material = get_material(material_id)
    if not material:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"success": True, "material": material})


@router.delete("/materials/{material_id}")
async def delete_material_endpoint(material_id: str):
    deleted = delete_material(material_id)
    if not deleted:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"success": True})


# ============================================================
# List / Search
# ============================================================

@router.get("")
async def list_assets():
    priors = get_all_priors()
    return JSONResponse({"success": True, "priors": priors, "count": len(priors)})


@router.get("/{prior_id}")
async def get_asset(prior_id: str):
    prior = get_prior(prior_id)
    if not prior:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"success": True, "prior": prior})


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


@router.post("/search")
async def search_assets(request: SearchRequest):
    results = search_priors(request.query, request.limit)
    return JSONResponse({"success": True, "results": results, "count": len(results)})


class SemanticSearchRequest(BaseModel):
    query: str
    max_results: int = 6


@router.post("/search/semantic")
async def semantic_search(request: SemanticSearchRequest):
    """Hybrid BM25 + vector search across all materials and priors."""
    try:
        results = await hybrid_search(request.query, max_results=request.max_results)
        return JSONResponse({
            "success": True,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "material_id": r.material_id,
                    "text": r.text,
                    "score": round(r.score, 4),
                }
                for r in results
            ],
            "count": len(results),
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
