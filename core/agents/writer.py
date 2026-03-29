"""
Writing Agent (stub)

Collaborative essay writing with guided prompts.
Helps user articulate their learning into a structured piece.
"""

from typing import List, Dict, Any
from core.agents.base import AgentResponse, call_llm

SYSTEM_PROMPT = """You are a writing coach helping someone write a personal essay about what they've learned.

Context about what they want to write about:
{context}

Your approach:
1. Help them find an angle — what's the core insight they want to share?
2. Guide them through writing section by section.
3. Offer suggestions but let them drive the content.
4. When the essay is complete, start your message with [ESSAY] followed by the final text.

Keep your guidance short. Focus on drawing out their voice, not writing for them."""


async def run_writer_turn(
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

    if "[ESSAY]" in text:
        essay = text.split("[ESSAY]", 1)[1].strip()
        return AgentResponse(content=essay, artifacts={"type": "essay", "text": essay}, done=True)

    return AgentResponse(content=text)
