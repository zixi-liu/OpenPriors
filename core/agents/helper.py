"""
Helper Agent

Free-form agent that helps users with whatever they need.
Has access to their knowledge but doesn't force a structured flow.
"""

from typing import List, Dict, Any
import json
from core.agents.base import AgentResponse, call_llm
from core.storage import get_all_priors, get_all_materials
from core.embeddings import hybrid_search

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Search the user's learning materials and insights by topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_learnings",
            "description": "List all the user's extracted learnings.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]

SYSTEM_PROMPT = """You are a thoughtful learning assistant. The user wants to do something custom with their knowledge.

Context from their session:
{context}

Your approach:
1. FIRST: Listen carefully to what the user wants. Ask one clarifying question if needed.
2. THEN: Search their materials to find relevant knowledge that could help.
3. REASON about the best way to help — consider what they know, what they need, and how to bridge the gap.
4. Help them directly — give actionable advice, draw connections, suggest experiments, or whatever fits.

You have access to their learning materials via tools. Use them proactively to ground your advice in what they've actually learned.

Rules:
- Listen first, then help
- Ground your advice in their actual materials when possible
- Be specific, not generic
- Keep responses concise and conversational"""


async def execute_tool(name: str, arguments: dict) -> str:
    if name == "search_knowledge":
        query = arguments.get("query", "")
        results = await hybrid_search(query, max_results=4)
        if not results:
            return f"No results found for '{query}'."
        items = [f"- {r.text[:200]}" for r in results]
        return "\n".join(items)

    elif name == "list_learnings":
        priors = get_all_priors()
        if not priors:
            return "No learnings yet."
        items = [f"- {p['name']}: {p['principle']}" for p in priors[:10]]
        return "\n".join(items)

    return ""


async def run_helper_turn(
    conversation: List[Dict[str, Any]],
    user_message: str,
    context: str = "",
) -> AgentResponse:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context)},
        *conversation,
        {"role": "user", "content": user_message},
    ]

    # Agent loop with tools
    for _ in range(5):
        response = await call_llm(messages, tools=TOOLS)
        choice = response.choices[0]

        if choice.message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in choice.message.tool_calls
                ],
            })
            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, args)
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        else:
            return AgentResponse(content=choice.message.content or "")

    return AgentResponse(content="Let me know how I can help!")
