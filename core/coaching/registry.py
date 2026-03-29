"""
Coaching Registry

Maps capability IDs to their handlers (sessions or workshops).
"""

from typing import Dict, Optional, Union

from .base import CoachingSession, WorkshopSkill
from .sessions import InterviewSession, CareerSession, NetworkingSession
from .workshops import FounderWorkshop


# Session handlers (structured roleplay + coaching tips)
SESSIONS: Dict[str, type[CoachingSession]] = {
    "mock_interview": InterviewSession,
    "interview": InterviewSession,
    "career": CareerSession,
    "networking": NetworkingSession,
}

# Workshop handlers (collaborative exploration)
WORKSHOPS: Dict[str, type[WorkshopSkill]] = {
    "founder": FounderWorkshop,
}


def get_handler(capability: str) -> Optional[Union[CoachingSession, WorkshopSkill]]:
    """
    Get a handler instance for a capability.

    Args:
        capability: The capability ID (e.g., "mock_interview", "founder")

    Returns:
        A new instance of the handler, or None if not found.
    """
    if capability in SESSIONS:
        return SESSIONS[capability]()
    elif capability in WORKSHOPS:
        return WORKSHOPS[capability]()
    return None


def is_session(capability: str) -> bool:
    """Check if a capability is a structured session."""
    return capability in SESSIONS


def is_workshop(capability: str) -> bool:
    """Check if a capability is a collaborative workshop."""
    return capability in WORKSHOPS
