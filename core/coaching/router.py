"""
Coaching Router

Routes coaching requests to the appropriate handler.
"""

from typing import Dict, Any, Optional, Tuple

from .base import CoachingSession, WorkshopSkill
from .registry import get_handler, is_session, is_workshop


async def handle_coaching_request(
    message: str,
    capability: str,
    context: Dict[str, Any],
    session_state: Optional[Dict[str, Any]] = None,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    """
    Route a coaching request to the appropriate handler.

    Args:
        message: User's message
        capability: The capability ID (e.g., "mock_interview", "founder")
        context: Context dict with user_context, scenario info, etc.
        session_state: Optional serialized session state to restore

    Returns:
        Tuple of (response, coaching_tip, updated_state)
        - response: The AI's response
        - coaching_tip: Coaching tip (for sessions) or None (for workshops)
        - updated_state: Serialized state for persistence
    """
    handler = get_handler(capability)

    if handler is None:
        return (
            "I'm not sure how to help with that. Please select a coaching mode.",
            None,
            {},
        )

    # Restore state if provided
    if session_state:
        handler.conversation_history = session_state.get("conversation_history", [])
        if hasattr(handler, "scenario"):
            handler.scenario = session_state.get("scenario")
        if hasattr(handler, "current_phase"):
            handler.current_phase = session_state.get("current_phase")

    # Handle based on handler type
    if isinstance(handler, CoachingSession):
        response, tip = await handler.handle_message(message, context)
        return response, tip, handler.to_dict()

    elif isinstance(handler, WorkshopSkill):
        response = await handler.execute(message, context)
        return response, None, handler.to_dict()

    return "An error occurred.", None, {}
