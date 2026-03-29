"""
Voice Capture Routes

Record what you learned by talking. Socratic Q&A flow probes what user learned.
Ported from coach-ai-prototype's story curation flow.
"""

import base64
import time

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List

from core.llm import complete, complete_json, parse_json
from core.storage import save_priors

router = APIRouter(prefix="/api/voice", tags=["voice"])


# --- Socratic Q&A (ported from coach-ai story.py) ---

class QAPair(BaseModel):
    question: str
    answer: str


class NextQuestionRequest(BaseModel):
    conversation: List[QAPair]


@router.post("/socratic/next-question")
async def next_question(req: NextQuestionRequest):
    """Generate the next Socratic question based on previous answers."""
    round_num = len(req.conversation)

    conversation_so_far = ""
    for qa in req.conversation:
        conversation_so_far += f"Q: {qa.question}\nA: {qa.answer}\n\n"

    if round_num == 0:
        round_guidance = """Ask what they learned recently. Be specific about learning.
Good: "What's something you read, watched, or heard recently that changed how you think?"
Bad: "Hey what's on your mind?" (too vague)"""
    elif round_num == 1:
        round_guidance = """Based on what they shared, ask where this principle shows up or is missing in their actual life.
Good: "Where in your daily life does this already show up? Where is it missing?"
Bad: "That sounds intriguing, tell me more" (too vague)"""
    else:
        round_guidance = """Help them commit to one specific, small action.
Good: "What's one thing you'll do differently this week because of this?"
Bad: "How do you feel about that?" (too vague)"""

    system_prompt = f"""You generate exactly ONE short question for a learning reflection session. Output ONLY the question, nothing else. No preamble, no commentary, no "That sounds interesting", no acknowledgment of their answer. Just the question.

{round_guidance}

Previous conversation:
{conversation_so_far}

After 3 rounds, respond with EXACTLY: "COMPLETE"

Output ONLY the question:"""

    response = await complete(
        prompt="",
        system_message=system_prompt,
        temperature=0.7,
        max_tokens=2000,
    )

    text = response.content.strip().strip('"')

    if "COMPLETE" in text or round_num >= 3:
        return JSONResponse({"question": "", "isComplete": True})

    return JSONResponse({"question": text, "isComplete": False})


# --- Audio capture ---

VOICE_EXTRACT_PROMPT = """You are an expert at helping people retain and apply what they learn.

The user just recorded themselves talking about something they recently learned.
This could be from ANY source — a book, podcast, YouTube video, conversation,
class, article, life experience, workshop, or their own reflection.

Your job:
1. Transcribe exactly what they said (if audio provided)
2. Extract actionable "priors" — principles they can practice in daily life

For each prior, provide:
- name: Short name (2-5 words)
- principle: The core insight in one sentence
- practice: A concrete way to practice this daily (specific, under 5 minutes)
- trigger: When/where in daily life to apply this
- source: What they were learning from

Return JSON:
{{
  "transcript": "exact words the user said",
  "title": "topic or source",
  "summary": "2-3 sentence summary",
  "priors": [
    {{
      "name": "...",
      "principle": "...",
      "practice": "...",
      "trigger": "...",
      "source": "..."
    }}
  ]
}}

Extract 3-7 priors. Return ONLY valid JSON."""


class VoiceTranscriptRequest(BaseModel):
    transcript: str
    source: Optional[str] = None


@router.post("/capture/audio")
async def capture_from_audio(
    audio: UploadFile = File(...),
    source: str = Form(default=""),
):
    start_time = time.time()
    try:
        audio_bytes = await audio.read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        content_type = audio.content_type or "audio/wav"
        audio_data_url = f"data:{content_type};base64,{audio_base64}"
        source_hint = f"\nThe user mentioned they were learning from: {source}" if source else ""

        from litellm import acompletion
        from core.llm import _set_api_key
        from core.config import get_model
        _set_api_key()

        messages = [{"role": "user", "content": [
            {"type": "file", "file": {"file_data": audio_data_url}},
            {"type": "text", "text": VOICE_EXTRACT_PROMPT + source_hint},
        ]}]

        model = get_model()
        if "gemini" not in model:
            model = "gemini/gemini-2.5-flash"

        response = await acompletion(model=model, messages=messages, temperature=0.3, max_tokens=4000)
        result = parse_json(response.choices[0].message.content)
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))

        return JSONResponse({
            "success": True,
            "transcript": result.get("transcript", ""),
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
            "latency_ms": round((time.time() - start_time) * 1000),
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/capture/transcript")
async def capture_from_transcript(request: VoiceTranscriptRequest):
    try:
        from core.extractor import extract_priors
        result = await extract_priors(request.transcript, source_hint=request.source or "")
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
