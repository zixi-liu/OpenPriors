"""
Founder Workshop Skill

Collaborative skill for helping founders work through business challenges.
Unlike coaching sessions, this is a flexible exploration without fixed phases.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List

from core.coaching.base import WorkshopSkill
from promptbase.modes.founder import FOUNDER_WORKSHOP, SKILLS as FOUNDER_SKILLS


@dataclass
class FounderWorkshop(WorkshopSkill):
    """
    Collaborative founder skill workshop.

    The AI acts as a co-founder and thought partner who:
    - Thinks WITH the user, not AT them
    - Offers concrete suggestions first (doesn't just ask questions)
    - Builds on user's ideas
    - Challenges constructively when needed

    No separate coaching tips - coaching is embedded in the collaborative conversation.
    """

    # Identity
    mode_id: str = "founder"
    name: str = "Founder Workshop"
    description: str = "Help founders work through business challenges collaboratively"

    # Prompts
    workshop_prompt: str = FOUNDER_WORKSHOP

    # Configuration
    tools: List[str] = field(default_factory=lambda: ["generate_artifact"])

    # Founder-specific state
    current_skill: str = ""  # clarity, monetization, storytelling, etc.

    def reset(self):
        """Reset skill state."""
        super().reset()
        self.current_skill = ""

    def _build_workshop_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build collaborative founder system prompt."""
        parts = []

        # Add workshop instructions
        if self.workshop_prompt:
            parts.append(self.workshop_prompt)

        # Add skill-specific content from existing FOUNDER_SKILLS (loaded from markdown files)
        self.current_skill = context.get("founder_skill", "")
        if self.current_skill and self.current_skill in FOUNDER_SKILLS:
            skill_content = FOUNDER_SKILLS[self.current_skill]
            parts.append(f"## FOUNDER SKILL: {self.current_skill.upper().replace('_', ' ')}\n{skill_content}")

        # Add user context
        if context.get("user_context"):
            parts.append(f"## FOUNDER'S BACKGROUND\n{context['user_context']}")

        # Add company context if available
        if context.get("company_description"):
            parts.append(f"## WHAT THEY'RE BUILDING\n{context['company_description']}")

        return "\n\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize skill state."""
        base = super().to_dict()
        base.update({
            "current_skill": self.current_skill,
        })
        return base
