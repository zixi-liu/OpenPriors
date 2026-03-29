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
from core.extractor import extract_priors, extract_from_url
from core.storage import save_priors, get_all_priors, search_priors, get_prior

router = APIRouter(prefix="/api/assets", tags=["assets"])


# ============================================================
# Upload (PDF, URL, text)
# ============================================================

class UploadTextRequest(BaseModel):
    content: str
    source: Optional[str] = None


class UploadURLRequest(BaseModel):
    url: str


@router.post("/upload/text")
async def upload_text(request: UploadTextRequest):
    try:
        result = await extract_priors(request.content, source_hint=request.source or "")
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))
        return JSONResponse({
            "success": True,
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/upload/url")
async def upload_url(request: UploadURLRequest):
    try:
        extracted = await extract_from_url(request.url)
        content = extracted.get("content", "")
        if not content:
            return JSONResponse({"success": False, "error": "Could not extract content from URL"})

        result = await extract_priors(content, source_hint=request.url)
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))
        return JSONResponse({
            "success": True,
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/upload/pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = content.decode("utf-8", errors="ignore")
        result = await extract_priors(text, source_hint=file.filename or "uploaded PDF")
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))
        return JSONResponse({
            "success": True,
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
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


@router.post("/voice/generate")
async def voice_generate(req: GenerateRequest):
    """Turn the voice Q&A conversation into extracted priors."""
    try:
        combined = "\n\n".join([
            f"Q: {qa.question}\nA: {qa.answer}"
            for qa in req.conversation
        ])
        result = await extract_priors(combined, source_hint="voice reflection")
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))
        return JSONResponse({
            "success": True,
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


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
