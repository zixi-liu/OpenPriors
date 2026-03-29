"""
Osmosis Session Routes

Conversational agent that helps users synthesize knowledge into daily life.
Sessions and messages are persisted in SQLite.
"""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

from core.agent import run_agent_turn
from core.storage import (
    create_session, get_session, get_all_sessions, update_session_title,
    delete_session, add_session_message, get_session_messages,
)

router = APIRouter(prefix="/api/osmosis", tags=["osmosis"])


# ============================================================
# Session CRUD
# ============================================================

@router.post("/sessions")
async def create_new_session():
    session_id = create_session()
    return JSONResponse({"success": True, "session_id": session_id})


@router.get("/sessions")
async def list_sessions():
    sessions = get_all_sessions()
    return JSONResponse({"success": True, "sessions": sessions})


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str):
    session = get_session(session_id)
    if not session:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    messages = get_session_messages(session_id)
    # Parse options JSON back to dicts
    for msg in messages:
        if msg.get("options"):
            try:
                msg["options"] = json.loads(msg["options"])
            except (json.JSONDecodeError, TypeError):
                msg["options"] = None
    return JSONResponse({"success": True, "session": session, "messages": messages})


@router.delete("/sessions/{session_id}")
async def delete_session_endpoint(session_id: str):
    deleted = delete_session(session_id)
    if not deleted:
        return JSONResponse({"success": False, "error": "Not found"}, status_code=404)
    return JSONResponse({"success": True})


class RenameRequest(BaseModel):
    title: str


@router.patch("/sessions/{session_id}")
async def rename_session(session_id: str, request: RenameRequest):
    update_session_title(session_id, request.title)
    return JSONResponse({"success": True})


# ============================================================
# Chat (with persistence)
# ============================================================

class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat")
async def osmosis_chat(request: ChatRequest):
    """Send a message in an osmosis session. Persists both user and assistant messages."""
    try:
        # Ensure session exists
        session = get_session(request.session_id)
        if not session:
            return JSONResponse({"success": False, "error": "Session not found"}, status_code=404)

        # Save user message
        add_session_message(request.session_id, "user", request.message)

        # Load conversation history from DB
        db_messages = get_session_messages(request.session_id)
        conversation = [{"role": m["role"], "content": m["content"]} for m in db_messages[:-1]]  # exclude the msg we just added

        # Run agent
        result = await run_agent_turn(conversation, request.message)

        # Save assistant response
        options_json = json.dumps(result.options) if result.options else None
        add_session_message(request.session_id, "assistant", result.content, options_json)

        # Auto-title: if this is the first real exchange (2 messages: greeting + user), generate title
        if len(db_messages) <= 2 and session["title"] == "New Session":
            # Use first few words of user message as title
            title = request.message[:50].strip()
            if len(request.message) > 50:
                title += "..."
            update_session_title(request.session_id, title)

        response: Dict[str, Any] = {
            "success": True,
            "message": result.content,
            "session_id": request.session_id,
        }
        if result.options:
            response["options"] = result.options

        return JSONResponse(response)

    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
