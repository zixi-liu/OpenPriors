"""
Reflection Agent

Walks the user through a structured Socratic reflection on a chosen topic/prior.
Asks 3-4 probing questions, then generates a written reflection.
"""

from typing import List, Dict, Any
from core.agents.base import AgentResponse, call_llm

SYSTEM_PROMPT = """You are a reflective learning coach guiding someone through a structured reflection.

Context about what they want to reflect on:
{context}

Your approach:
1. You guide the user through 3-4 Socratic questions, one at a time.
2. Each question builds on their previous answer — go deeper, not wider.
3. Use these techniques:
   - "Where in your life does this show up?"
   - "What would change if you fully embraced this?"
   - "What's the gap between knowing this and doing this?"
   - "What's one thing you'll do differently this week?"
4. After 3-4 exchanges, generate a final written reflection that synthesizes their answers.

When you're ready to generate the final reflection, start your message with [REFLECTION] followed by the reflection text. This should be a 200-400 word first-person narrative that weaves their answers into a coherent insight.

Keep your questions short and conversational (1-2 sentences). Be warm but push them to go deeper."""


async def run_reflection_turn(
    conversation: List[Dict[str, Any]],
    user_message: str,
    context: str = "",
) -> AgentResponse:
    """Run one turn of the reflection agent."""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        *conversation,
        {"role": "user", "content": user_message},
    ]

    response = await call_llm(messages)
    text = response.choices[0].message.content or ""

    # Check if the agent generated a final reflection
    if "[REFLECTION]" in text:
        reflection = text.split("[REFLECTION]", 1)[1].strip()
        return AgentResponse(
            content=reflection,
            artifacts={"type": "reflection", "text": reflection},
            done=True,
        )

    return AgentResponse(content=text)
