"""
Base classes for the Coaching Framework.

CoachingSession: Structured roleplay with coaching tips
WorkshopSkill: Collaborative exploration without fixed phases
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum


class SessionPhase(Enum):
    """Standard phases for coaching sessions."""
    SETUP = "setup"
    SCENARIO = "scenario"
    ACTIVE = "active"
    COMPLETE = "complete"


@dataclass
class CoachingSession(ABC):
    """
    Base class for structured coaching sessions.

    A coaching session has two AI personas working together:
    1. Roleplay persona - Plays the interviewer/manager/contact
    2. Coach persona - Provides real-time tips to the user

    Flow: Scenario Generation → Roleplay Exchanges → Coaching Tips → Optional Evaluation

    Example:
        class InterviewSession(CoachingSession):
            mode_id = "interview"
            name = "Mock Interview"
            roleplay_prompt = INTERVIEWER_ROLEPLAY
            coaching_prompt = COACHING_SKILL
            has_evaluation = True
    """

    # Identity
    mode_id: str = ""
    name: str = ""
    description: str = ""

    # Prompts (from promptbase/modes/)
    roleplay_prompt: str = ""      # AI plays interviewer/manager/contact
    coaching_prompt: str = ""      # Coach provides real-time tips

    # Configuration
    phases: List[str] = field(default_factory=lambda: ["setup", "scenario", "active", "complete"])
    has_scenario: bool = True      # Whether to generate scenario at start
    has_evaluation: bool = False   # Whether to evaluate at end

    # Runtime state (reset per session)
    current_phase: str = "setup"
    scenario: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    def reset(self):
        """Reset session state for a new session."""
        self.current_phase = "setup"
        self.scenario = None
        self.conversation_history = []

    async def start(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start a new coaching session.

        Args:
            context: Session context (user info, settings, etc.)

        Returns:
            dict with scenario and initial state
        """
        self.reset()

        if self.has_scenario:
            self.scenario = await self.generate_scenario(context)
            self.current_phase = "scenario"
        else:
            self.current_phase = "active"

        return {
            "scenario": self.scenario,
            "phase": self.current_phase,
            "ai_role": self.get_ai_role(context),
        }

    async def generate_scenario(self, context: Dict[str, Any]) -> str:
        """
        Generate the starting scenario.

        Override in subclasses for custom scenario generation.
        Default calls the existing /api/voice/generate-scenario logic.
        """
        # Import here to avoid circular imports
        from routes.voice import generate_scenario_internal

        result = await generate_scenario_internal(
            mode=self.mode_id,
            context=context,
        )
        return result.get("scenario", "")

    async def handle_message(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> Tuple[str, Optional[str]]:
        """
        Handle a user message during the session.

        Args:
            message: User's message
            context: Session context

        Returns:
            Tuple of (roleplay_response, coaching_tip)
        """
        # Move to active phase if needed
        if self.current_phase == "scenario":
            self.current_phase = "active"

        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Get roleplay response (AI as interviewer/manager/etc.)
        roleplay_response = await self._get_roleplay_response(message, context)

        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": roleplay_response})

        # Get coaching tip (separate from roleplay)
        coaching_tip = await self._get_coaching_tip(context)

        return roleplay_response, coaching_tip

    async def _get_roleplay_response(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Get response from the roleplay persona.

        Uses self.roleplay_prompt to instruct the AI.
        """
        from core.llm_client import LLMClient, ModelType

        client = LLMClient()

        # Build system prompt with roleplay instructions
        system_prompt = self._build_roleplay_system_prompt(context)

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in self.conversation_history[:-1]:  # Exclude the just-added user message
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": message})

        # Call LLM
        response = await client.complete_chat(
            messages=messages,
            model=ModelType.GPT5_1.value,
            temperature=0.7,
        )

        return response.content

    def _build_roleplay_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build the system prompt for roleplay responses."""
        parts = []

        # Add scenario context if available
        if self.scenario:
            parts.append(f"## SCENARIO\n{self.scenario}")

        # Add roleplay instructions
        if self.roleplay_prompt:
            # Fill in template variables
            filled_prompt = self.roleplay_prompt.format(
                company=context.get("company", "a tech company"),
                level=context.get("level", "Senior"),
                role=context.get("role", "Software Engineer"),
                ai_role=context.get("ai_role", "the other person"),
                conversation_type=context.get("conversation_type", "professional conversation"),
                **context.get("template_vars", {}),
            )
            parts.append(filled_prompt)

        # Add user context if available
        if context.get("user_context"):
            parts.append(f"## USER CONTEXT\n{context['user_context']}")

        return "\n\n".join(parts)

    async def _get_coaching_tip(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Get a coaching tip for the current exchange.

        Uses existing /api/voice/coaching logic.
        """
        try:
            from routes.voice import get_coaching_tip_internal

            tip = await get_coaching_tip_internal(
                mode=self.mode_id,
                conversation=self.conversation_history,
                context=context,
            )
            return tip
        except Exception as e:
            print(f"Warning: Could not get coaching tip: {e}")
            return None

    async def end(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        End the session and optionally evaluate.

        Returns:
            Evaluation results if has_evaluation=True, else None
        """
        self.current_phase = "complete"

        if self.has_evaluation:
            return await self.evaluate(context)

        return None

    async def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate session performance.

        Override in subclasses for custom evaluation logic.
        """
        return {
            "evaluated": False,
            "message": "No evaluation configured for this session type",
        }

    def get_ai_role(self, context: Dict[str, Any]) -> str:
        """Get the AI role label for this session."""
        return context.get("ai_role", "Assistant")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state to dict."""
        return {
            "mode_id": self.mode_id,
            "name": self.name,
            "current_phase": self.current_phase,
            "scenario": self.scenario,
            "conversation_history": self.conversation_history,
        }


@dataclass
class WorkshopSkill:
    """
    Base class for collaborative workshop skills.

    Unlike CoachingSession, workshops don't have:
    - Fixed phases
    - Separate roleplay/coach personas
    - Scenario generation

    Instead, they provide:
    - A collaborative persona that thinks WITH the user
    - Flexible conversation flow
    - Optional artifact generation

    Example:
        class FounderWorkshop(WorkshopSkill):
            mode_id = "founder"
            name = "Founder Workshop"
            description = "Help founders work through business challenges"
            workshop_prompt = FOUNDER_WORKSHOP
    """

    # Identity
    mode_id: str = ""
    name: str = ""
    description: str = ""     # When to use this skill

    # Prompts
    workshop_prompt: str = ""  # Collaborative persona instructions

    # Configuration
    tools: List[str] = field(default_factory=list)  # Available tools

    # Runtime state
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    def reset(self):
        """Reset skill state for a new session."""
        self.conversation_history = []

    async def execute(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> str:
        """
        Handle a user message collaboratively.

        Unlike CoachingSession, this returns only one response
        (no separate coaching tip - coaching is embedded in the conversation).

        Args:
            message: User's message
            context: Session context

        Returns:
            Collaborative response
        """
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Get collaborative response
        response = await self._get_workshop_response(message, context)

        # Add assistant response to history
        self.conversation_history.append({"role": "assistant", "content": response})

        return response

    async def _get_workshop_response(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> str:
        """Get collaborative response from workshop persona."""
        from core.llm_client import LLMClient, ModelType

        client = LLMClient()

        # Build system prompt
        system_prompt = self._build_workshop_system_prompt(context)

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history
        for msg in self.conversation_history[:-1]:  # Exclude just-added user message
            messages.append(msg)

        # Add current user message
        messages.append({"role": "user", "content": message})

        # Call LLM
        response = await client.complete_chat(
            messages=messages,
            model=ModelType.GPT5_1.value,
            temperature=0.7,
        )

        return response.content

    def _build_workshop_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build the system prompt for workshop responses."""
        parts = []

        # Add workshop instructions
        if self.workshop_prompt:
            parts.append(self.workshop_prompt)

        # Add user context if available
        if context.get("user_context"):
            parts.append(f"## USER CONTEXT\n{context['user_context']}")

        # Add skill-specific context
        if context.get("skill_context"):
            parts.append(f"## SKILL CONTEXT\n{context['skill_context']}")

        return "\n\n".join(parts)

    async def generate_artifact(
        self,
        artifact_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate an artifact from the workshop.

        Args:
            artifact_type: Type of artifact to generate
            context: Context including conversation history

        Returns:
            Generated artifact
        """
        from core.artifacts import generate_artifact

        # Include conversation history in context
        artifact_context = {
            **context,
            "conversation_history": self.conversation_history,
        }

        return await generate_artifact(artifact_type, artifact_context)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize skill state to dict."""
        return {
            "mode_id": self.mode_id,
            "name": self.name,
            "description": self.description,
            "conversation_history": self.conversation_history,
        }
