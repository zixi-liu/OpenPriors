"""
Interview Coaching Session

Structured mock interview practice with:
- Scenario generation (interview setup)
- Roleplay as interviewer (probing follow-ups)
- Real-time coaching tips (STAR guidance)
- Session evaluation (rubric-based)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.coaching.base import CoachingSession
from promptbase.modes.interview import INTERVIEWER_ROLEPLAY, COACHING_SKILL


@dataclass
class InterviewSession(CoachingSession):
    """
    Mock interview coaching session.

    The AI plays a behavioral interviewer who:
    - Asks the BQ question from the scenario
    - Probes for STAR details (Situation, Task, Action, Result)
    - Identifies red flags (vagueness, missing ownership, no metrics)
    - Asks follow-up questions to strengthen the answer

    The coach provides:
    - Real-time tips on what the interviewer is looking for
    - STAR structure guidance
    - Level-calibrated expectations
    """

    # Identity
    mode_id: str = "interview"
    name: str = "Mock Interview"
    description: str = "Practice behavioral interviews with real-time coaching"

    # Prompts
    roleplay_prompt: str = INTERVIEWER_ROLEPLAY
    coaching_prompt: str = COACHING_SKILL

    # Configuration
    phases: List[str] = field(default_factory=lambda: ["setup", "scenario", "qa_loop", "evaluation"])
    has_scenario: bool = True
    has_evaluation: bool = True

    # Interview-specific state
    bq_category: Optional[str] = None
    current_question: Optional[str] = None
    questions_asked: int = 0
    max_questions: int = 3

    def reset(self):
        """Reset session state."""
        super().reset()
        self.bq_category = None
        self.current_question = None
        self.questions_asked = 0

    async def generate_scenario(self, context: Dict[str, Any]) -> str:
        """
        Generate interview scenario with BQ question.

        Uses existing /api/voice/generate-scenario endpoint logic.
        """
        # Store BQ category for later use
        self.bq_category = context.get("bq_category")

        # Call existing scenario generation
        from routes.voice import generate_scenario as voice_generate_scenario
        from pydantic import BaseModel

        # Build request matching ScenarioRequest
        class ScenarioRequest(BaseModel):
            mode: str = "interview"
            bqCategory: Optional[str] = None
            sampleQuestions: Optional[List[str]] = None
            userContext: Optional[str] = None
            targetCompany: Optional[str] = None
            targetRole: Optional[str] = None
            targetLevel: Optional[str] = None

        # Note: We're calling the internal logic, not the HTTP endpoint
        # For now, we'll use a simplified version
        from core.llm_client import LLMClient, ModelType
        import random

        client = LLMClient()

        # Get sample questions
        sample_questions = context.get("sample_questions", [])
        if sample_questions:
            self.current_question = random.choice(sample_questions)
        else:
            self.current_question = "Tell me about a challenging situation you faced."

        target_company = context.get("company", "a tech company")
        target_role = context.get("role", "Software Engineer")
        target_level = context.get("level", "Senior")

        prompt = f"""Generate a brief interview scenario with scene-setting AND the first question.

TARGET COMPANY: {target_company}
TARGET ROLE: {target_role}
TARGET LEVEL: {target_level}
BQ CATEGORY: {self.bq_category or "behavioral"}

CANDIDATE'S BACKGROUND:
{context.get("user_context", "No specific context provided")}

QUESTION TO ASK (use this EXACT question):
"{self.current_question}"

Write a scenario that:
1. Sets the scene (2-3 sentences) at {target_company}
2. Creates a realistic interviewer persona
3. Ends by asking the EXACT question provided above

Write in FIRST PERSON as the interviewer speaking to the candidate.
Keep it natural and realistic. Output the scene + question only."""

        response = await client.complete(
            prompt=prompt,
            model=ModelType.GPT4O.value,  # Use GPT-4o for scenario generation (faster)
            temperature=0.8,
            max_tokens=300,
        )

        self.questions_asked = 1
        return response.content.strip()

    async def handle_message(
        self,
        message: str,
        context: Dict[str, Any],
    ) -> tuple[str, Optional[str]]:
        """
        Handle user's answer to interview question.

        The interviewer will:
        1. Acknowledge the answer briefly
        2. Probe for missing STAR elements
        3. Ask a follow-up question
        """
        # Add interview-specific context
        context["bq_category"] = self.bq_category
        context["current_question"] = self.current_question
        context["questions_asked"] = self.questions_asked

        return await super().handle_message(message, context)

    def _build_roleplay_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build interviewer system prompt with STAR probing instructions."""
        parts = []

        # Add scenario context
        if self.scenario:
            parts.append(f"## SCENARIO\n{self.scenario}")

        # Add interview-specific context
        parts.append(f"""## INTERVIEW CONTEXT
- BQ Category: {self.bq_category or "general behavioral"}
- Current Question: {self.current_question or "Tell me about a time..."}
- Questions Asked: {self.questions_asked}/{self.max_questions}
- Target Level: {context.get("level", "Senior")}
- Target Company: {context.get("company", "Tech Company")}""")

        # Add roleplay instructions (with filled template)
        if self.roleplay_prompt:
            filled_prompt = self.roleplay_prompt.format(
                company=context.get("company", "a tech company"),
                level=context.get("level", "Senior"),
                role=context.get("role", "Software Engineer"),
            )
            parts.append(filled_prompt)

        # Add user context (resume/JD)
        if context.get("user_context"):
            parts.append(f"## CANDIDATE BACKGROUND\n{context['user_context']}")

        return "\n\n".join(parts)

    async def next_question(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Move to the next BQ question.

        Returns the new question, or None if max questions reached.
        """
        if self.questions_asked >= self.max_questions:
            return None

        # Get a new question
        sample_questions = context.get("sample_questions", [])
        if sample_questions:
            import random
            self.current_question = random.choice(sample_questions)
        else:
            self.current_question = f"Tell me about another time when you {self.bq_category or 'faced a challenge'}."

        self.questions_asked += 1
        return self.current_question

    async def evaluate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate interview performance with rubric.

        Uses existing evaluation logic from /api/analysis.
        """
        try:
            from routes.analysis import evaluate_interview_internal

            result = await evaluate_interview_internal(
                conversation=self.conversation_history,
                bq_category=self.bq_category,
                level=context.get("level", "Senior"),
                context=context,
            )
            return result
        except Exception as e:
            print(f"Warning: Could not evaluate interview: {e}")
            return {
                "evaluated": False,
                "error": str(e),
            }

    def get_ai_role(self, context: Dict[str, Any]) -> str:
        """Get interviewer role label."""
        return "Interviewer"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state."""
        base = super().to_dict()
        base.update({
            "bq_category": self.bq_category,
            "current_question": self.current_question,
            "questions_asked": self.questions_asked,
            "max_questions": self.max_questions,
        })
        return base
