"""
Networking Coaching Session

Structured networking practice with:
- Scenario selection (conference, coffee chat, etc.)
- Roleplay as networking contact (mirrors energy)
- Real-time coaching tips (AIR, FORD, AAA frameworks)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.coaching.base import CoachingSession
from promptbase.modes.networking import NETWORKING_CONTACT_ROLEPLAY, COACHING_SKILL


@dataclass
class NetworkingSession(CoachingSession):
    """
    Networking roleplay coaching session.

    The AI plays a networking contact who:
    - Mirrors the user's energy level
    - Rewards genuine curiosity and punishes generic behavior
    - Has their own interests and limited attention
    - Responds naturally (not always helpfully)

    The coach provides:
    - Framework suggestions (AIR, FORD, AAA, NAME, GIVE)
    - Energy level feedback
    - Conversation flow guidance
    """

    # Identity
    mode_id: str = "networking"
    name: str = "Networking Practice"
    description: str = "Practice networking with real-time coaching"

    # Prompts
    roleplay_prompt: str = NETWORKING_CONTACT_ROLEPLAY
    coaching_prompt: str = COACHING_SKILL

    # Configuration
    phases: List[str] = field(default_factory=lambda: ["setup", "scenario", "practice", "debrief"])
    has_scenario: bool = True
    has_evaluation: bool = False

    # Networking-specific state
    scenario_type: Optional[str] = None  # conference, coffee_chat, meetup, casual
    contact_type: Optional[str] = None   # PM at Stripe, VC at A16Z, etc.

    def reset(self):
        """Reset session state."""
        super().reset()
        self.scenario_type = None
        self.contact_type = None

    async def generate_scenario(self, context: Dict[str, Any]) -> str:
        """
        Generate networking scenario.

        For networking, scenarios are often pre-defined and selected by user,
        but we can also generate them dynamically.
        """
        self.scenario_type = context.get("scenario_type", "conference")
        self.contact_type = context.get("contact_type")

        # If a pre-defined scenario was provided, use it
        if context.get("scenario_text"):
            return context["scenario_text"]

        from core.llm_client import LLMClient, ModelType

        client = LLMClient()

        # Scenario contexts
        scenario_contexts = {
            "conference": "at a tech conference during a coffee break",
            "coffee_chat": "at a coffee chat arranged through a mutual connection",
            "meetup": "at an industry meetup event",
            "casual": "at a casual social gathering with tech folks",
        }

        # Default contact types
        default_contacts = {
            "conference": "a Product Manager at a well-known tech company",
            "coffee_chat": "someone senior in your target field",
            "meetup": "a fellow attendee who seems interesting",
            "casual": "someone who works in tech",
        }

        context_desc = scenario_contexts.get(self.scenario_type, "at a professional event")
        self.contact_type = self.contact_type or default_contacts.get(self.scenario_type, "a professional contact")

        prompt = f"""Generate a brief networking scenario.

SETTING: {context_desc}
CONTACT: {self.contact_type}

USER'S BACKGROUND:
{context.get("user_context", "A tech professional looking to expand their network")}

Write a scenario that:
1. Sets the scene briefly (1-2 sentences)
2. Describes who the contact is and why they might be interesting
3. Ends with the natural moment where conversation could start

Keep it realistic and natural. The user will initiate the conversation.
Don't include any dialogue yet - just set the scene."""

        response = await client.complete(
            prompt=prompt,
            model=ModelType.GPT4O.value,
            temperature=0.8,
            max_tokens=200,
        )

        return response.content.strip()

    def _build_roleplay_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build networking contact system prompt."""
        parts = []

        # Add scenario context
        if self.scenario:
            parts.append(f"## SCENARIO\n{self.scenario}")

        # Add networking-specific context
        parts.append(f"""## NETWORKING CONTEXT
- Setting: {self.scenario_type or "professional event"}
- You are: {self.contact_type or "a professional contact"}""")

        # Add roleplay instructions
        if self.roleplay_prompt:
            filled_prompt = self.roleplay_prompt.format(
                contact_type=self.contact_type or "a professional contact",
                scenario_context=self.scenario_type or "a professional setting",
            )
            parts.append(filled_prompt)

        # Add user context
        if context.get("user_context"):
            parts.append(f"## USER'S BACKGROUND (they don't know you have this)\n{context['user_context']}")

        return "\n\n".join(parts)

    def get_ai_role(self, context: Dict[str, Any]) -> str:
        """Get the contact role label."""
        return self.contact_type or "Contact"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state."""
        base = super().to_dict()
        base.update({
            "scenario_type": self.scenario_type,
            "contact_type": self.contact_type,
        })
        return base
