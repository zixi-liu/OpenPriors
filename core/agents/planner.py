"""
Planner Agent

Creates a practice plan with daily/weekly goals linked to priors.
Saves goals to the database with cadence and check-in schedules.
"""

import json
from typing import List, Dict, Any
from core.agents.base import AgentResponse, call_llm
from core.storage import create_goal, get_all_priors
from core.embeddings import hybrid_search

SYSTEM_PROMPT = """You are a practice plan designer helping someone integrate learning into their daily life.

Context about what they want to practice:
{context}

Their extracted priors (actionable principles):
{priors}

Your approach:
1. First, ask the user about their current routine and what cadence works for them (daily, every 2 days, weekly).
2. Based on their priors and preferences, design a concrete practice plan.
3. When ready, output the plan as JSON by starting your message with [PLAN] followed by a JSON array:

[PLAN]
{{
  "title": "Plan title",
  "goals": [
    {{
      "description": "Specific daily action to take",
      "prior_name": "Name of the related prior",
      "cadence": "daily|every_2_days|weekly"
    }}
  ]
}}

Each goal should be:
- Specific and actionable (not vague)
- Under 5 minutes to do
- Tied to a real moment in their day (e.g., "before your first meeting", "during lunch")

Keep conversations short. Ask 1-2 questions max before generating the plan.
Generate 3-5 goals per plan."""


async def run_planner_turn(
    conversation: List[Dict[str, Any]],
    user_message: str,
    context: str = "",
) -> AgentResponse:
    """Run one turn of the planner agent."""

    # Get user's priors for context
    priors = get_all_priors()
    priors_text = "\n".join([
        f"- {p['name']}: {p['principle']} (Practice: {p['practice']})"
        for p in priors[:10]
    ]) if priors else "No priors extracted yet."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT.format(context=context, priors=priors_text)},
        *conversation,
        {"role": "user", "content": user_message},
    ]

    response = await call_llm(messages)
    text = response.choices[0].message.content or ""

    # Check if the agent generated a plan
    if "[PLAN]" in text:
        plan_json = text.split("[PLAN]", 1)[1].strip()
        # Strip markdown code fences if present
        if plan_json.startswith("```"):
            plan_json = plan_json.split("\n", 1)[1] if "\n" in plan_json else plan_json[3:]
            if plan_json.endswith("```"):
                plan_json = plan_json[:-3].strip()

        try:
            plan = json.loads(plan_json)
            goals_created = []

            for goal in plan.get("goals", []):
                # Find matching prior
                prior_id = ""
                for p in priors:
                    if p["name"].lower() in goal.get("prior_name", "").lower():
                        prior_id = p["id"]
                        break

                goal_id = create_goal(
                    description=goal["description"],
                    prior_id=prior_id,
                    cadence=goal.get("cadence", "daily"),
                )
                goals_created.append({
                    "id": goal_id,
                    "description": goal["description"],
                    "cadence": goal.get("cadence", "daily"),
                })

            summary = f"**{plan.get('title', 'Practice Plan')}**\n\n"
            for i, g in enumerate(goals_created, 1):
                cadence_label = {"daily": "Daily", "every_2_days": "Every 2 days", "weekly": "Weekly"}.get(g["cadence"], g["cadence"])
                summary += f"{i}. {g['description']} ({cadence_label})\n"
            summary += f"\n{len(goals_created)} goals created. I'll check in with you based on the cadence you set."

            return AgentResponse(
                content=summary,
                artifacts={"type": "plan", "goals": goals_created, "title": plan.get("title", "Practice Plan")},
                done=True,
            )
        except (json.JSONDecodeError, KeyError) as e:
            return AgentResponse(content=f"I had trouble creating the plan. Let me try again. Error: {e}")

    return AgentResponse(content=text)
