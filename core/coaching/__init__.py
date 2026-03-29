"""
Coaching Framework

A clean architecture for AI coaching sessions and workshop skills.

Two main patterns:
1. CoachingSession - Structured roleplay with coaching tips (Interview, Career, Networking)
2. WorkshopSkill - Collaborative exploration (Founder, Research, Decompress)

Usage:
    from core.coaching import get_handler, handle_coaching_request

    # Route a request
    response, tip = await handle_coaching_request(message, capability, context)

    # Or get handler directly
    handler = get_handler("mock_interview")
    if isinstance(handler, CoachingSession):
        response, tip = await handler.handle_message(message, context)
"""

from .base import CoachingSession, WorkshopSkill, SessionPhase
from .registry import (
    get_handler,
    is_session,
    is_workshop,
    SESSIONS,
    WORKSHOPS,
)
from .router import handle_coaching_request

__all__ = [
    # Base classes
    "CoachingSession",
    "WorkshopSkill",
    "SessionPhase",
    # Registry
    "get_handler",
    "is_session",
    "is_workshop",
    "SESSIONS",
    "WORKSHOPS",
    # Router
    "handle_coaching_request",
]
