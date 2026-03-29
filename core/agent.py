"""
Explore Agent

A tool-using agent that helps users synthesize their learnings into daily life.
Uses OpenAI function calling to reason about what tools to use.

Flow:
1. User opens Osmosis Session
2. Agent lists their materials, asks what they want to work on
3. Agent searches relevant priors/chunks via semantic search
4. Agent reasons about how this knowledge applies to their life
5. Agent proposes options (guided essay, practice plan, roleplay, etc.)
6. User picks one → Agent guides them through it
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from core.embeddings import hybrid_search
from core.storage import get_all_materials, get_all_priors, get_material


# ============================================================
# Tool definitions (OpenAI function calling format)
# ============================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_materials",
            "description": "List all learning materials the user has uploaded or captured. Returns titles, types, and summaries.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge",
            "description": "Semantic search across all the user's learning materials and extracted priors. Use this to find relevant knowledge based on a topic or question.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "What to search for (e.g., 'dealing with pressure', 'communication techniques', 'habit formation')",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_material_detail",
            "description": "Get the full content of a specific learning material by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "material_id": {
                        "type": "string",
                        "description": "The material ID to retrieve",
                    },
                },
                "required": ["material_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_priors",
            "description": "Get all extracted priors (actionable principles) from the user's learning materials.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_options",
            "description": "Present options to the user for how to synthesize their knowledge into their life. Call this after you've gathered enough context about their knowledge and goals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "options": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Short title for the option"},
                                "description": {"type": "string", "description": "What this option involves"},
                                "type": {"type": "string", "enum": ["guided_reflection", "practice_plan", "roleplay", "integration_essay", "custom"]},
                            },
                            "required": ["title", "description", "type"],
                        },
                        "description": "3-5 options tailored to the user's specific knowledge and situation",
                    },
                },
                "required": ["options"],
            },
        },
    },
]


SYSTEM_PROMPT = """You are an Osmosis Coach — you help people integrate what they've learned into their daily life.

You have access to the user's learning materials (books, articles, podcasts, reflections) and extracted priors (actionable principles).

Your approach:
1. Start by understanding what the user wants to work on. List their materials so they can pick, or ask what's on their mind.
2. Use search_knowledge to find relevant priors and material chunks. Don't guess — actually search.
3. Reason about how this knowledge connects to their real life. Look for patterns across materials.
4. Propose 3-5 specific options for how they can synthesize this knowledge, tailored to what you found. Always include a free-form "Something else" option.

Options you might propose (not limited to these):
- Write a guided reflection connecting this knowledge to a specific life situation
- Create a weekly practice plan with daily micro-exercises
- Roleplay a scenario where they apply these principles
- Design an integration plan that weaves multiple priors together
- Build a personal framework combining insights from different sources

Be warm, curious, and specific. Reference actual content from their materials — don't be generic.
Keep responses concise. This is a conversation, not an essay."""


# ============================================================
# Tool execution
# ============================================================

async def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool and return the result as a string."""

    if name == "list_materials":
        materials = get_all_materials()
        if not materials:
            return "No materials yet. The user hasn't uploaded any learning materials."
        items = []
        for m in materials:
            items.append(f"- [{m['id']}] {m['title']} ({m['source_type']}) — {m.get('summary', '')[:100]}")
        return f"User has {len(materials)} materials:\n" + "\n".join(items)

    elif name == "search_knowledge":
        query = arguments.get("query", "")
        results = await hybrid_search(query, max_results=6)
        if not results:
            return f"No results found for '{query}'."
        items = []
        for r in results:
            items.append(f"[score: {r.score:.2f}, material: {r.material_id}]\n{r.text[:300]}")
        return f"Found {len(results)} relevant chunks:\n\n" + "\n\n---\n\n".join(items)

    elif name == "get_material_detail":
        material_id = arguments.get("material_id", "")
        material = get_material(material_id)
        if not material:
            return f"Material '{material_id}' not found."
        return f"Title: {material['title']}\nType: {material['source_type']}\nSummary: {material.get('summary', '')}\n\nContent:\n{material['content'][:3000]}"

    elif name == "get_all_priors":
        priors = get_all_priors()
        if not priors:
            return "No priors extracted yet."
        items = []
        for p in priors:
            items.append(f"- {p['name']}: {p['principle']} (Practice: {p['practice']})")
        return f"{len(priors)} priors:\n" + "\n".join(items)

    elif name == "propose_options":
        # This is a terminal tool — the options get returned to the frontend
        return json.dumps(arguments)

    return f"Unknown tool: {name}"


# ============================================================
# Agent loop
# ============================================================

@dataclass
class AgentMessage:
    role: str  # "user", "assistant", "tool"
    content: str
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None
    options: Optional[List[dict]] = None  # populated when propose_options is called


async def run_agent_turn(
    conversation: List[Dict[str, Any]],
    user_message: str,
) -> AgentMessage:
    """
    Run one turn of the agent. May involve multiple tool calls before responding.
    Returns the agent's final response (text or options).
    """
    from openai import AsyncOpenAI
    import os

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        from core.config import get_api_key
        api_key = get_api_key("openai")

    client = AsyncOpenAI(api_key=api_key)

    # Build messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(conversation)
    messages.append({"role": "user", "content": user_message})

    # Agent loop — keep calling until we get a text response (no more tool calls)
    max_iterations = 8
    for _ in range(max_iterations):
        response = await client.chat.completions.create(
            model="o3-mini",
            messages=messages,
            tools=TOOLS,
            temperature=0.7,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls" or choice.message.tool_calls:
            # Execute each tool call
            assistant_msg = {
                "role": "assistant",
                "content": choice.message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in choice.message.tool_calls
                ],
            }
            messages.append(assistant_msg)

            for tc in choice.message.tool_calls:
                args = json.loads(tc.function.arguments)
                result = await execute_tool(tc.function.name, args)

                # Check if this is propose_options — return options to frontend
                if tc.function.name == "propose_options":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                    return AgentMessage(
                        role="assistant",
                        content=choice.message.content or "Here are some ways to work with this knowledge:",
                        options=args.get("options", []),
                    )

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            # Text response — return it
            return AgentMessage(
                role="assistant",
                content=choice.message.content or "",
            )

    # Fallback if max iterations reached
    return AgentMessage(
        role="assistant",
        content="I've been thinking about this but need your help to narrow it down. What specific area of your life would you like to apply your learnings to?",
    )
