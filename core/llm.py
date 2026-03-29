"""
OpenPriors LLM Client

Thin wrapper around litellm. Supports any provider via BYOK config.
"""

import json
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from litellm import acompletion

from core.config import get_api_key, get_model


@dataclass
class LLMResponse:
    content: str
    model: str
    usage: Optional[Dict[str, int]] = None


def _set_api_key():
    """Push BYOK key into env so litellm picks it up."""
    from core.config import load_config
    config = load_config()
    provider = config.get("llm", {}).get("provider", "gemini")
    key = get_api_key(provider)
    if not key:
        return

    env_map = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }
    env_var = env_map.get(provider)
    if env_var and not os.environ.get(env_var):
        os.environ[env_var] = key


async def complete(
    prompt: str,
    system_message: str = "",
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 4000,
) -> LLMResponse:
    _set_api_key()

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    use_model = model or get_model()
    response = await acompletion(
        model=use_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content
    usage = None
    if hasattr(response, "usage") and response.usage:
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return LLMResponse(content=content, model=use_model, usage=usage)


async def complete_json(
    prompt: str,
    system_message: str = "",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    response = await complete(prompt, system_message, model, temperature=0.3, max_tokens=16000)
    return parse_json(response.content)


def parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code blocks — try all matches, not just first
    for code_block in re.finditer(r'```(?:json)?\s*([\s\S]*?)```', text):
        try:
            return json.loads(code_block.group(1).strip())
        except json.JSONDecodeError:
            continue

    # Find outermost JSON object
    start = text.find('{')
    if start != -1:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not parse JSON from: {text[:200]}...")
