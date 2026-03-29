"""
Osmosis Agent

A proactive agent that runs on a schedule to help users build habits
from their extracted priors. It checks what's due, crafts personalized
check-in messages, and logs responses.

The agent doesn't just ask "did you do it?" — it connects the prior
back to the user's life context, offers encouragement based on streaks,
and adapts based on past responses.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from core.storage import (
    get_due_goals,
    get_active_goals,
    get_goal_check_ins,
    get_all_priors,
    get_prior,
    record_check_in,
)

logger = logging.getLogger("openpriors.osmosis")


async def generate_check_in_message(goal: Dict[str, Any]) -> str:
    """Generate a personalized check-in message for a goal."""
    from core.llm import complete

    # Get the linked prior if any
    prior_context = ""
    if goal.get("prior_id"):
        prior = get_prior(goal["prior_id"])
        if prior:
            prior_context = f"""
Linked prior:
- Name: {prior['name']}
- Principle: {prior['principle']}
- Practice: {prior['practice']}
- Trigger: {prior.get('trigger_context', '')}
"""

    # Get recent check-in history
    check_ins = get_goal_check_ins(goal["id"])
    history = ""
    if check_ins:
        recent = check_ins[:5]
        history = "Recent check-ins:\n"
        for ci in recent:
            status = "practiced" if ci["practiced"] else "skipped"
            history += f"- {ci['created_at'][:10]}: {status}"
            if ci.get("response"):
                history += f" — \"{ci['response'][:100]}\""
            history += "\n"

    streak = goal.get("streak", 0)
    total = goal.get("total_check_ins", 0)

    prompt = f"""You are the Osmosis agent — a warm, encouraging coach that helps people build habits from what they've learned.

Write a short Slack check-in message (2-4 sentences) for this goal:

Goal: {goal['description']}
{prior_context}
Current streak: {streak} days
Total check-ins: {total}
{history}

Guidelines:
- Be warm and specific — reference the actual practice, not generic motivation
- If streak > 0, acknowledge it naturally (don't over-celebrate)
- If streak is 0, be encouraging without guilt
- If they've been skipping, gently ask what's getting in the way
- End with a simple question they can respond to
- Keep it casual — this is a Slack message, not an essay
- Don't use emojis excessively

Return ONLY the message text."""

    response = await complete(prompt, temperature=0.7, max_tokens=300)
    return response.content.strip()


async def get_due_check_ins() -> List[Dict[str, Any]]:
    """Get all goals that are due for a check-in, with generated messages."""
    due_goals = get_due_goals()
    check_ins = []

    for goal in due_goals:
        try:
            message = await generate_check_in_message(goal)
            check_ins.append({
                "goal_id": goal["id"],
                "goal_description": goal["description"],
                "prior_id": goal.get("prior_id", ""),
                "slack_channel": goal.get("slack_channel", ""),
                "streak": goal.get("streak", 0),
                "message": message,
            })
        except Exception as e:
            logger.error(f"Failed to generate check-in for goal {goal['id']}: {e}")

    return check_ins


async def process_check_in_response(goal_id: str, user_response: str) -> str:
    """Process a user's response to a check-in and return a follow-up."""
    from core.llm import complete

    # Determine if they practiced
    classify_prompt = f"""The user responded to a habit check-in. Did they practice or not?

Response: "{user_response}"

Return JSON: {{"practiced": true/false, "confidence": "high/low"}}
Return ONLY valid JSON."""

    from core.llm import complete_json
    result = await complete_json(classify_prompt)
    practiced = result.get("practiced", False)

    # Record the check-in
    record_check_in(goal_id, user_response, practiced)

    # Generate follow-up
    if practiced:
        follow_up_prompt = f"""The user just confirmed they practiced their habit. Write a brief (1-2 sentence) encouraging response. Be genuine, not over the top. Reference what they said: "{user_response[:200]}"

Return ONLY the message."""
    else:
        follow_up_prompt = f"""The user indicated they didn't practice their habit today. Write a brief (1-2 sentence) supportive response. No guilt — just understanding and a gentle nudge. Reference what they said: "{user_response[:200]}"

Return ONLY the message."""

    response = await complete(follow_up_prompt, temperature=0.7, max_tokens=150)
    return response.content.strip()
