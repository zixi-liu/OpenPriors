"""
Base agent class for specialized sub-agents.
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import os

from openai import AsyncOpenAI


@dataclass
class AgentResponse:
    content: str
    artifacts: Optional[Dict[str, Any]] = None  # saved data (reflection, plan, etc.)
    done: bool = False  # whether this agent's flow is complete


async def call_llm(
    messages: List[Dict[str, Any]],
    model: str = "o3-mini",
    tools: Optional[List[dict]] = None,
) -> Any:
    """Shared LLM call for all agents."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        from core.config import get_api_key
        api_key = get_api_key("openai")

    client = AsyncOpenAI(api_key=api_key)
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
    }
    if tools:
        params["tools"] = tools

    return await client.chat.completions.create(**params)
