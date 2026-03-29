"""
Coach Agent (stub)

Roleplay practice where the AI plays a scenario and the user practices applying their priors.
Uses voice recording (Talk about a learning flow).
"""

from typing import List, Dict, Any
from core.agents.base import AgentResponse, call_llm

SYSTEM_PROMPT = """You are a practice coach helping someone apply what they've learned through roleplay.

Context about what they want to practice:
{context}

Your approach:
1. Set up a realistic scenario where they need to apply their learning.
2. Play the other person in the scenario.
3. After the roleplay, give brief feedback on how they applied the principles.
4. Keep exchanges short — this is voice-paced.

When the roleplay is done, start your message with [DONE] followed by a brief summary of how they did."""


async def run_coach_turn(
    conversation: List[Dict[str, Any]],
    user_message: str,
    context: str = "",
) -> AgentResponse:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        *conversation,
        {"role": "user", "content": user_message},
    ]

    response = await call_llm(messages)
    text = response.choices[0].message.content or ""

    if "[DONE]" in text:
        summary = text.split("[DONE]", 1)[1].strip()
        return AgentResponse(content=summary, artifacts={"type": "coaching_summary", "text": summary}, done=True)

    return AgentResponse(content=text)
