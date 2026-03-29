"""
Career Coaching Session

Structured workplace conversation practice with:
- Scenario generation (workplace situation)
- Roleplay as manager/colleague (realistic pushback)
- Real-time coaching tips (power dynamics, tactics)
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

from core.coaching.base import CoachingSession
from promptbase.modes.career import MANAGER_ROLEPLAY, COACHING_SKILL


@dataclass
class CareerSession(CoachingSession):
    """
    Career roleplay coaching session.

    The AI plays a workplace character (manager, colleague, HR) who:
    - Responds realistically to the user's approach
    - Uses typical workplace dynamics (deflection, constraints)
    - Pushes back when appropriate
    - Has their own agenda and perspective

    The coach provides:
    - Power dynamics analysis
    - Manipulation detection
    - Tactical suggestions
    """

    # Identity
    mode_id: str = "career"
    name: str = "Career Coaching"
    description: str = "Practice workplace conversations with real-time coaching"

    # Prompts
    roleplay_prompt: str = MANAGER_ROLEPLAY
    coaching_prompt: str = COACHING_SKILL

    # Configuration
    phases: List[str] = field(default_factory=lambda: ["setup", "scenario", "roleplay", "debrief"])
    has_scenario: bool = True
    has_evaluation: bool = False

    # Career-specific state
    conversation_type: Optional[str] = None  # 1on1, promotion, feedback, negotiation, conflict
    ai_role: Optional[str] = None            # Your Manager, Direct Report, HR, etc.

    def reset(self):
        """Reset session state."""
        super().reset()
        self.conversation_type = None
        self.ai_role = None

    async def generate_scenario(self, context: Dict[str, Any]) -> str:
        """
        Generate workplace scenario.

        Uses existing /api/voice/generate-scenario endpoint logic.
        """
        self.conversation_type = context.get("conversation_type", "1on1")
        self.ai_role = context.get("ai_role")

        from core.llm_client import LLMClient, ModelType
        import random

        client = LLMClient()

        # Conversation type contexts
        type_context = {
            "1on1": "a regular 1:1 meeting with your manager",
            "promotion": "a conversation about your readiness for promotion",
            "feedback": "giving constructive feedback to a direct report",
            "negotiation": "negotiating compensation or role details",
            "conflict": "addressing a conflict or disagreement with a colleague",
        }

        # Default AI roles by conversation type
        default_roles = {
            "1on1": "Your Engineering Manager",
            "promotion": "Your Manager",
            "feedback": "Your Direct Report",
            "negotiation": "Hiring Manager",
            "conflict": "Your Colleague",
        }

        context_desc = type_context.get(self.conversation_type, "a workplace conversation")
        self.ai_role = self.ai_role or default_roles.get(self.conversation_type, "Your Manager")

        # FAANG-specific scenario templates — sourced from real workplace situations (Blind, 一亩三分地, etc.)
        # Each template includes: concrete numbers, named features/projects, specific stakes
        # Randomly select 2-3 templates as few-shot examples for variety
        scenario_templates = {
            "1on1": [
                # Performance edge cases
                "Perf reviews are coming up and your manager mentioned you're 'on the edge' between Meets and Exceeds. You led the checkout latency project that cut p95 from 1.2s to 400ms, but they say you need 'more cross-team visibility.'",
                "You've been on the Search Relevance team for 18 months. You shipped 3 major features but your manager says you need to 'broaden your scope' before they can support L5.",
                "Your manager told you your 'performance hasn't been meeting expectations — mainly around how you approach and deliver projects.' No PIP yet, but you've only completed 4 of your last 7 sprint stories.",
                # Org changes and uncertainty
                "Your skip-level scheduled a surprise 1:1. Rumors say the 40-person Infra org is getting split — half going to Cloud, half staying. Your manager has been unusually quiet about it.",
                "Your team is being merged with Platform. Your manager says 'nothing changes for you' but 3 of 8 engineers on the other team got moved to different orgs last month.",
                "Leadership just announced a 15% headcount reduction. Your manager hasn't said anything, but your project (internal tooling) isn't revenue-generating.",
                # Manager relationship issues
                "Your manager has been giving you vague feedback for 6 months. When you ask for specifics, they say 'you're doing fine' but your peer got promoted and you didn't.",
                "You've noticed your manager gives the high-visibility projects to a colleague who joined 8 months after you. Your last 3 projects were maintenance work.",
                "Your manager promised you'd lead the new authentication service 4 months ago. Last week they assigned it to someone else without explanation.",
                # Career growth concerns
                "You've been L4 for 2.5 years. Your manager says you need 'more senior behaviors' but won't specify what that means. Your TLR score was 'Meets Expectations.'",
                "Your skip-level asked to meet 1:1. You don't know if this is routine or if something's wrong. Your manager mentioned last week that 'leadership is watching the team closely.'",
                "You want to transfer to the ML team but your manager says 'we need you here for at least another 6 months.' You've already been on the current team for 2 years.",
            ],
            "promotion": [
                # Vague feedback loops
                "You got 'Exceeds Expectations' after shipping the real-time fraud detection system that blocked $4M in fraudulent transactions. But you still didn't get promoted to L5. Your manager says you need 'more impact' but won't specify what's missing.",
                "You're up for Staff but the feedback is that you need 'more org-wide influence.' You already drove the company-wide observability rollout across 12 teams, but your skip-level says 'the committee didn't see enough evidence.'",
                "Your manager says you're 'almost ready' for L5 — the same thing they said 2 cycles ago. You've shipped the payment reconciliation system and mentored 2 junior engineers.",
                # Unfair comparisons
                "A colleague with 18 months less tenure just got promoted to Senior after one high-visibility launch. You've shipped 3 projects including the API gateway migration, and you've been told you're 'almost there' for 3 cycles.",
                "Your peer got promoted to L6 after leading the homepage redesign. You led the entire backend migration (50K lines, zero downtime) but it 'wasn't visible enough' to leadership.",
                "An engineer who joined your team 6 months ago is being put up for promotion. You've been here 2 years and trained them on the codebase.",
                # Committee and process issues
                "Your manager advocated for your promotion but the committee rejected it, citing 'need to see sustained performance for another half.' You've had 'Exceeds' for 3 consecutive cycles.",
                "The promo committee said you need 'more leadership' but you've been TL for 8 months and shipped 2 major features. Your manager says they 'did their best.'",
                "You were told you're ready for L5 in January. It's now October and your manager says 'the calibration was tough this cycle — maybe next time.'",
                # Level disputes
                "You got an L5 offer from Google at $380K TC, but you're currently L5 at Meta making $350K. You believe your 6 years of distributed systems experience justify L6.",
                "HR downleveled you from Senior to Mid during the offer stage, citing 'calibration.' The recruiter originally said you'd be L5.",
                "Your internal transfer was approved but at your current level. The hiring manager said 'we can discuss promotion after 6 months' but nothing is in writing.",
            ],
            "feedback": [
                # Underperformance
                "Your L5 report has completed only 2 of their last 8 sprint stories since getting promoted 4 months ago. Their peer on the Notifications team is picking up the overflow.",
                "Your report has missed 4 of their last 6 sprint commitments by 30-40%. They committed to the search autocomplete feature in Sprint 22 and delivered it in Sprint 24.",
                "Your direct report's code reviews have a 40% rejection rate. Other engineers have started avoiding pairing with them. They seem unaware of the issue.",
                # Interpersonal issues
                "Your senior engineer wrote a design doc review that said the ML team's approach was 'fundamentally flawed' in a public doc with 40+ viewers. The ML lead has refused to attend their next review.",
                "Your senior engineer openly said in retro that 'this team's technical decisions are made by committee and it's killing velocity.' Two junior engineers have told you they feel demotivated.",
                "Your report interrupts others in meetings and dismisses junior engineers' suggestions. You've gotten 3 anonymous complaints through the feedback system.",
                # Attitude and growth
                "Your report has been late to standup 12 times this month and missed 2 sprint planning sessions. When you mentioned it, they said 'async is more efficient anyway.'",
                "Your direct report pushed back hard when you gave them constructive feedback. They said 'that's just your opinion' and 'the old manager never had a problem with it.'",
                "Your report is technically strong but refuses to document their work. Three people have asked you to intervene because they can't onboard to the codebase.",
                # PIP territory
                "HR told you to put your report on a formal performance plan. The report doesn't know yet. You have a 1:1 with them in 30 minutes.",
                "Your report's performance has been declining since they got passed over for promotion 3 months ago. Their PRs are sloppy and they've been disengaged in meetings.",
                "You need to tell your report that their project is being reassigned because stakeholders lost confidence. They've been working on it for 4 months.",
            ],
            "negotiation": [
                # Competing offers
                "You got an L5 offer from Google at $380K TC, but you're currently L5 at Meta making $350K. You believe your 6 years of distributed systems experience justify L6 ($450K+ TC).",
                "Your competing offer from Stripe is $420K TC — 30% higher than your current $320K. But your current team has great WLB and you're 8 months from a $50K equity cliff.",
                "You have a competing offer at $395K TC. Your current company countered with a 10% base bump plus 1.5x RSU multiplier, but no level change.",
                # Level disputes
                "The initial offer is E5 at $365K TC but you have 8 years of experience and led a team of 6. Levels.fyi shows E6 median at $480K. The recruiter says 'leveling is final.'",
                "The offer came in $50K below your ask. The recruiter said 'our bands are tight' but you know from Blind that the top of band is $40K higher.",
                "You're being lowballed at L4 when you're currently L5. The hiring manager loves you but says 'we can promote you after 6 months' — nothing in writing.",
                # Recruiter tactics
                "The recruiter said bringing up your Intel counter-offer was 'unprofessional.' They're now ghosting you. You really want this job but don't want to seem desperate.",
                "The recruiter keeps saying 'this is our best offer' but won't put you in touch with the hiring manager. You've heard the HM has more flexibility.",
                "The startup offered 0.1% equity but won't share the cap table or latest valuation. They're asking you to decide by Friday.",
                # Internal negotiations
                "You expressed dissatisfaction with your salary. Now your manager wants to 'chat about your career development.' You're not sure if this is retention or deflection.",
                "You asked for a raise after getting Exceeds. Your manager said 'I'll see what I can do' 6 weeks ago and hasn't mentioned it since.",
                "You got an external offer. Your manager asked what it would take to keep you. You're not sure if you should share the number or just leave.",
            ],
            "conflict": [
                # PM conflicts
                "Your PM changed the search ranking requirements twice this sprint — first adding personalization, then removing it. The team lost 4 days of work and sprint completion dropped to 60%.",
                "Your PM committed to a feature deadline without consulting engineering. It's technically impossible in the timeframe. When you raised it, they said 'figure it out.'",
                "The PM keeps adding 'small' requests mid-sprint that each take 2-3 days. Your velocity is down 40% and leadership thinks engineering is underperforming.",
                # Design conflicts
                "Your designer insists on a custom animation framework for the onboarding flow that would add 2 weeks to the timeline. When you proposed Lottie instead, they escalated to their Director.",
                "The designer says your implementation 'doesn't match the mocks' but the differences are 2px margins. They've blocked the PR review for 3 days.",
                "Design wants to overhaul the checkout flow right before Black Friday. Engineering estimates 6 weeks; they're asking for 2. The PM is caught in the middle.",
                # Credit stealing
                "A colleague on the Growth team presented your A/B testing framework as their own work at the quarterly all-hands. The framework drove a 12% improvement in activation rate.",
                "Your coworker keeps repeating your ideas in meetings with leadership as if they thought of them. It's happened 4 times now. You mentioned it to them privately and they denied it.",
                "You left for a competitor for 6 months, then returned. The project you built (95% complete) was presented by your replacement as their work to the VP.",
                # Ownership disputes
                "The ML platform team is claiming ownership of the recommendation pipeline you built 6 months ago. Their v1 doesn't support your custom ranking model that drives 18% of revenue.",
                "A senior engineer on the Ads team publicly called out 3 latency regressions in your payments service design doc during the company-wide architecture review.",
                "Another team's tech lead keeps making architectural decisions that affect your service without consulting you. When you raised it, they said 'we're moving fast.'",
                # Cross-team friction
                "The DevOps team is blaming your service for the outage last week. Your logs show the issue was in their deployment pipeline, but they have leadership's ear.",
                "You need an API from another team. They've deprioritized it twice and your launch is now delayed 3 weeks. Your manager says 'work it out with them.'",
                "A peer engineer told your manager you're 'difficult to work with' after you pushed back on their design. You don't know what specifically they said.",
            ],
        }

        all_examples = scenario_templates.get(self.conversation_type, scenario_templates["1on1"])
        # Select 2-3 random templates as few-shot examples (rotate for variety)
        num_examples = min(3, len(all_examples))
        selected_examples = random.sample(all_examples, num_examples)
        examples_text = "\n".join(f"- {ex}" for ex in selected_examples)

        company = context.get("company", "a FAANG company")

        prompt = f"""Generate a brief, realistic workplace scenario for: {context_desc}

COMPANY: {company}
CONVERSATION TYPE: {self.conversation_type}
AI ROLE: {self.ai_role}

STYLE REFERENCE — notice the specificity (numbers, project names, concrete stakes). Generate something DIFFERENT:
{examples_text}

USER'S BACKGROUND:
{context.get("user_context", "No specific context provided")}

REQUIREMENTS:
1. Create a NEW scenario — do NOT reuse topics from the examples above
2. Include SPECIFIC details: project names, metrics, timelines, dollar amounts
3. Set up the situation in 2-3 sentences with clear tension
4. End with the AI character's opening line IN CHARACTER as {self.ai_role}

Write the AI's opening line in FIRST PERSON.
Keep it realistic for {company}. Use tech company terminology."""

        response = await client.complete(
            prompt=prompt,
            model=ModelType.GPT4O.value,
            temperature=0.8,
            max_tokens=300,
        )

        return response.content.strip()

    def _build_roleplay_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build manager/colleague system prompt."""
        parts = []

        # Add scenario context
        if self.scenario:
            parts.append(f"## SCENARIO\n{self.scenario}")

        # Add career-specific context
        parts.append(f"""## CONVERSATION CONTEXT
- Conversation Type: {self.conversation_type or "workplace conversation"}
- Your Role: {self.ai_role or "Manager"}
- Company: {context.get("company", "Tech Company")}""")

        # Add roleplay instructions
        if self.roleplay_prompt:
            filled_prompt = self.roleplay_prompt.format(
                ai_role=self.ai_role or "the manager",
                conversation_type=self.conversation_type or "workplace conversation",
            )
            parts.append(filled_prompt)

        # Add user context
        if context.get("user_context"):
            parts.append(f"## USER'S BACKGROUND\n{context['user_context']}")

        return "\n\n".join(parts)

    def get_ai_role(self, context: Dict[str, Any]) -> str:
        """Get the AI role label."""
        return self.ai_role or "Manager"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state."""
        base = super().to_dict()
        base.update({
            "conversation_type": self.conversation_type,
            "ai_role": self.ai_role,
        })
        return base
