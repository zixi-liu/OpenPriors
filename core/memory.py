"""
Memory-Based Context (Empathy Layer 2)

Fetches past sessions from Firebase and generates personalized context
based on user's history with a specific coach.

Signals extracted:
- Session count and frequency
- Topics/capabilities practiced
- Struggles and growth areas
- Improvement trajectory
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

# Firebase
_firestore_client = None


def get_firestore():
    """Get Firestore client, initializing if needed."""
    global _firestore_client

    if _firestore_client is not None:
        return _firestore_client if _firestore_client else None

    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        try:
            firebase_admin.get_app()
        except ValueError:
            cred_json = (
                os.environ.get('FIREBASE_ADMIN_JSON') or
                os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON') or
                os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')
            )
            cred_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
            elif cred_json:
                import json
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
            else:
                firebase_admin.initialize_app()

        _firestore_client = firestore.client(database_id='ai-coach')
        return _firestore_client
    except Exception as e:
        print(f"⚠️ Firebase not available for memory: {e}")
        _firestore_client = False
        return None


# ============================================================
# Data Classes
# ============================================================

@dataclass
class SessionSummary:
    """Summary of a past coaching session."""
    session_id: str
    date: datetime
    capability: str  # mock_interview, career, etc.
    bq_category: Optional[str]
    message_count: int
    summary: Optional[str]
    key_insights: List[str]


@dataclass
class MemoryContext:
    """Memory-based context for personalized coaching."""
    # Session patterns
    total_sessions: int
    sessions_this_week: int
    days_since_last_session: int

    # What they've worked on
    capabilities_practiced: Dict[str, int]  # capability -> count
    bq_categories_practiced: Dict[str, int]  # category -> count

    # Insights from past sessions
    recent_summaries: List[str]  # Last 3 session summaries
    all_insights: List[str]  # Collected key insights

    # Inferred growth areas
    most_practiced: Optional[str]  # What they focus on most
    least_practiced: Optional[str]  # Potential gap

    # For prompt injection
    context_for_coach: str


# ============================================================
# Fetch Past Sessions
# ============================================================

def fetch_user_sessions(
    user_id: str,
    persona_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch recent conversations between user and a specific coach.

    Args:
        user_id: Firebase user ID
        persona_id: Coach persona ID
        limit: Max sessions to fetch

    Returns:
        List of conversation documents
    """
    db = get_firestore()
    if not db:
        return []

    try:
        # Query conversations for this user-coach pair
        conversations_ref = db.collection('users').document(user_id).collection('conversations')
        query = conversations_ref.where('personaId', '==', persona_id).order_by('updatedAt', direction='DESCENDING').limit(limit)

        docs = query.stream()
        sessions = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            sessions.append(data)

        return sessions
    except Exception as e:
        print(f"⚠️ Error fetching sessions: {e}")
        return []


def parse_session(session_data: Dict[str, Any]) -> SessionSummary:
    """Parse a session document into a SessionSummary."""
    metadata = session_data.get('metadata', {})
    messages = session_data.get('messages', [])

    # Parse date
    updated_at = session_data.get('updatedAt')
    if hasattr(updated_at, 'timestamp'):
        # Firestore Timestamp
        date = datetime.fromtimestamp(updated_at.timestamp())
    elif isinstance(updated_at, datetime):
        date = updated_at
    else:
        date = datetime.now()

    return SessionSummary(
        session_id=session_data.get('id', ''),
        date=date,
        capability=metadata.get('capability', 'general'),
        bq_category=metadata.get('bqCategory'),
        message_count=len(messages),
        summary=metadata.get('summary'),
        key_insights=metadata.get('keyInsights', [])
    )


# ============================================================
# Analyze Session History
# ============================================================

def analyze_sessions(sessions: List[SessionSummary]) -> MemoryContext:
    """
    Analyze session history to generate memory context.

    Args:
        sessions: List of parsed sessions (most recent first)

    Returns:
        MemoryContext with patterns and insights
    """
    if not sessions:
        return MemoryContext(
            total_sessions=0,
            sessions_this_week=0,
            days_since_last_session=-1,
            capabilities_practiced={},
            bq_categories_practiced={},
            recent_summaries=[],
            all_insights=[],
            most_practiced=None,
            least_practiced=None,
            context_for_coach="This is a new user with no prior sessions."
        )

    now = datetime.now()
    week_ago = now - timedelta(days=7)

    # Count sessions
    total_sessions = len(sessions)
    sessions_this_week = sum(1 for s in sessions if s.date > week_ago)

    # Days since last session
    days_since_last = (now - sessions[0].date).days

    # Capability counts
    capabilities: Dict[str, int] = {}
    bq_categories: Dict[str, int] = {}

    for session in sessions:
        cap = session.capability or 'general'
        capabilities[cap] = capabilities.get(cap, 0) + 1

        if session.bq_category:
            bq_categories[session.bq_category] = bq_categories.get(session.bq_category, 0) + 1

    # Recent summaries (last 3)
    recent_summaries = [s.summary for s in sessions[:3] if s.summary]

    # All insights
    all_insights = []
    for s in sessions:
        all_insights.extend(s.key_insights)
    # Deduplicate and limit
    all_insights = list(dict.fromkeys(all_insights))[:10]

    # Most/least practiced
    most_practiced = max(capabilities, key=capabilities.get) if capabilities else None

    # For least practiced, consider standard categories they haven't done
    standard_bq = ['conflict', 'failure', 'leadership', 'teamwork', 'ownership', 'ambiguity']
    unpracticed = [c for c in standard_bq if c not in bq_categories]
    least_practiced = unpracticed[0] if unpracticed else None

    # Build context string
    context_for_coach = build_context_string(
        total_sessions=total_sessions,
        sessions_this_week=sessions_this_week,
        days_since_last=days_since_last,
        capabilities=capabilities,
        bq_categories=bq_categories,
        recent_summaries=recent_summaries,
        all_insights=all_insights,
        least_practiced=least_practiced
    )

    return MemoryContext(
        total_sessions=total_sessions,
        sessions_this_week=sessions_this_week,
        days_since_last_session=days_since_last,
        capabilities_practiced=capabilities,
        bq_categories_practiced=bq_categories,
        recent_summaries=recent_summaries,
        all_insights=all_insights,
        most_practiced=most_practiced,
        least_practiced=least_practiced,
        context_for_coach=context_for_coach
    )


def build_context_string(
    total_sessions: int,
    sessions_this_week: int,
    days_since_last: int,
    capabilities: Dict[str, int],
    bq_categories: Dict[str, int],
    recent_summaries: List[str],
    all_insights: List[str],
    least_practiced: Optional[str]
) -> str:
    """Build natural language context for the coach."""

    parts = []

    # Session frequency
    if total_sessions == 0:
        parts.append("This is your first session with this user.")
    elif total_sessions == 1:
        parts.append("You've had 1 previous session with this user.")
    else:
        parts.append(f"You've had {total_sessions} sessions with this user.")

    # Recent activity
    if sessions_this_week > 0:
        parts.append(f"They've been active - {sessions_this_week} session(s) this week.")
    elif days_since_last > 7:
        parts.append(f"It's been {days_since_last} days since their last session - welcome them back.")

    # What they've practiced
    if bq_categories:
        top_categories = sorted(bq_categories.items(), key=lambda x: x[1], reverse=True)[:3]
        practiced = ", ".join([f"{cat} ({count}x)" for cat, count in top_categories])
        parts.append(f"BQ categories practiced: {practiced}")

    # Gap areas
    if least_practiced:
        parts.append(f"They haven't practiced '{least_practiced}' questions yet - consider exploring this.")

    # Past insights (if any)
    if all_insights:
        parts.append("Key insights from past sessions:")
        for insight in all_insights[:3]:
            parts.append(f"  - {insight}")

    # Recent summary
    if recent_summaries and recent_summaries[0]:
        parts.append(f"Last session summary: {recent_summaries[0][:200]}...")

    return "\n".join(parts)


# ============================================================
# Main API
# ============================================================

def get_memory_context(
    user_id: str,
    persona_id: str,
    max_sessions: int = 10
) -> Optional[MemoryContext]:
    """
    Get memory-based context for a user-coach pair.

    Args:
        user_id: Firebase user ID
        persona_id: Coach persona ID
        max_sessions: Max past sessions to analyze

    Returns:
        MemoryContext or None if no history
    """
    # Fetch sessions
    raw_sessions = fetch_user_sessions(user_id, persona_id, limit=max_sessions)

    if not raw_sessions:
        return None

    # Parse sessions
    sessions = [parse_session(s) for s in raw_sessions]

    # Analyze
    return analyze_sessions(sessions)


def get_memory_context_for_prompt(
    user_id: str,
    persona_id: str
) -> str:
    """
    Get memory context as a string ready for prompt injection.

    Returns empty string if no history.
    """
    context = get_memory_context(user_id, persona_id)

    if not context:
        return ""

    return f"""
## USER HISTORY WITH YOU

{context.context_for_coach}

Use this context to personalize your coaching. Reference their past work when relevant.
Don't explicitly mention "I see from our history..." - just naturally incorporate the context.
"""


# ============================================================
# CLI for testing
# ============================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python memory.py <user_id> <persona_id>")
        sys.exit(1)

    user_id = sys.argv[1]
    persona_id = sys.argv[2]

    print(f"\n{'='*60}")
    print(f"Memory Context for {user_id} with {persona_id}")
    print(f"{'='*60}\n")

    context = get_memory_context(user_id, persona_id)

    if context:
        print(f"Total sessions: {context.total_sessions}")
        print(f"Sessions this week: {context.sessions_this_week}")
        print(f"Days since last: {context.days_since_last_session}")
        print(f"Capabilities: {context.capabilities_practiced}")
        print(f"BQ Categories: {context.bq_categories_practiced}")
        print(f"Most practiced: {context.most_practiced}")
        print(f"Least practiced: {context.least_practiced}")
        print(f"\nRecent summaries: {context.recent_summaries}")
        print(f"\nAll insights: {context.all_insights}")
        print(f"\n{'='*60}")
        print("CONTEXT FOR COACH:")
        print(f"{'='*60}")
        print(context.context_for_coach)
    else:
        print("No session history found.")
