"""
Voice Capture Routes

Record what you learned by talking. AI transcribes and extracts priors.
Includes Socratic Q&A flow that probes what user learned.
"""

import base64
import json
import time

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from core.llm import complete, complete_json, parse_json
from core.storage import save_priors

router = APIRouter(prefix="/api/voice", tags=["voice"])


# --- Socratic Q&A ---

FIRST_QUESTION_PROMPT = """You are a Socratic learning coach. The user wants to share something they recently learned.

Generate the FIRST question to ask them. It should be open-ended and inviting, like:
- "What did you learn recently that excited you?"
- "What's something you read or heard that made you think differently?"

Return JSON:
{{"question": "your question here"}}

Return ONLY valid JSON."""


FOLLOWUP_QUESTION_PROMPT = """You are a Socratic learning coach helping someone deeply process what they learned.

Here is the conversation so far:
{conversation}

Based on their answers, generate the NEXT probing question. Use Socratic techniques:
- Ask them to explain WHY this matters to them
- Ask for a concrete example or scenario where they'd apply this
- Challenge assumptions gently ("What would happen if the opposite were true?")
- Ask how this connects to something they already know
- Ask what they'd do differently starting tomorrow

This is question {question_number} of 3. {"Make this the final question — ask something that helps them commit to a specific action or practice." if question_number == 3 else ""}

Return JSON:
{{"question": "your question here"}}

Return ONLY valid JSON."""


class SocraticRequest(BaseModel):
    conversation: List[Dict[str, str]]  # [{question, answer}, ...]
    question_number: int


@router.post("/socratic/first-question")
async def get_first_question():
    """Get the first Socratic question to start the Q&A."""
    try:
        result = await complete_json(FIRST_QUESTION_PROMPT)
        return JSONResponse({
            "success": True,
            "question": result.get("question", "What did you learn recently that excited you?"),
        })
    except Exception as e:
        return JSONResponse({
            "success": True,
            "question": "What did you learn recently that excited you?",
        })


@router.post("/socratic/next-question")
async def get_next_question(request: SocraticRequest):
    """Get the next Socratic follow-up question based on conversation so far."""
    try:
        convo_text = "\n".join([
            f"Q: {qa['question']}\nA: {qa['answer']}"
            for qa in request.conversation
        ])

        prompt = FOLLOWUP_QUESTION_PROMPT.format(
            conversation=convo_text,
            question_number=request.question_number,
        )

        result = await complete_json(prompt)
        return JSONResponse({
            "success": True,
            "question": result.get("question", "Can you tell me more about that?"),
        })
    except Exception as e:
        return JSONResponse({
            "success": True,
            "question": "Can you tell me more about that?",
        })


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
- trigger: When/where in daily life to apply this (e.g., "when writing an email", "before a difficult conversation", "while reading")
- source: What they were learning from (book title, podcast name, etc.)

Return JSON:
{{
  "transcript": "exact words the user said (verbatim transcription)",
  "title": "topic or source they were talking about",
  "summary": "2-3 sentence summary of what they learned",
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

Extract 3-7 priors. Focus on what's most actionable and life-changing.
Return ONLY valid JSON."""


class VoiceTranscriptRequest(BaseModel):
    transcript: str
    source: Optional[str] = None


@router.post("/capture/audio")
async def capture_from_audio(
    audio: UploadFile = File(...),
    source: str = Form(default=""),
):
    """
    Upload audio (WAV/MP3) of user talking about what they learned.
    Gemini transcribes and extracts priors in one call.
    """
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

        messages = [
            {"role": "user", "content": [
                {"type": "file", "file": {"file_data": audio_data_url}},
                {"type": "text", "text": VOICE_EXTRACT_PROMPT + source_hint},
            ]}
        ]

        model = get_model()
        if "gemini" not in model:
            model = "gemini/gemini-2.5-flash"

        response = await acompletion(
            model=model,
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )

        result = parse_json(response.choices[0].message.content)
        priors = result.get("priors", [])
        ids = save_priors(priors, source_title=result.get("title", ""))

        elapsed_ms = (time.time() - start_time) * 1000

        return JSONResponse({
            "success": True,
            "transcript": result.get("transcript", ""),
            "title": result.get("title", ""),
            "summary": result.get("summary", ""),
            "priors_count": len(ids),
            "priors": priors,
            "ids": ids,
            "latency_ms": round(elapsed_ms),
        })

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/capture/transcript")
async def capture_from_transcript(request: VoiceTranscriptRequest):
    """
    Frontend did STT already, sends us the transcript.
    We extract priors from the text.
    """
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
