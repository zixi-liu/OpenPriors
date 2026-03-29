"""
Memory Service

Provides memory extraction and retrieval using Mem0 + Qdrant.
Each user has isolated memories scoped by their Firebase user_id.

Two-step extraction process:
1. Classify document type (resume, JD, meeting notes, etc.)
2. Use document-specific extraction prompt for optimal fact extraction
"""

import os
import json
from typing import Optional, List, Dict, Any
from mem0 import Memory
from openai import OpenAI

# Singleton instance
_memory_service: Optional["MemoryService"] = None

# =============================================================================
# Document Classification
# =============================================================================

DOCUMENT_TYPES = [
    "resume",
    "job_description",
    "meeting_notes",
    "performance_review",
    "project_document",
    "pitch_deck",
    "general_notes",
]

CLASSIFICATION_PROMPT = """Classify this document into ONE of these categories:
- resume: A person's CV/resume with work history, skills, education
- job_description: A job posting with requirements and responsibilities
- meeting_notes: Notes from a meeting, 1:1, or discussion
- performance_review: Feedback, review, or evaluation of performance
- project_document: Technical doc, PRD, design doc, or project spec
- pitch_deck: Startup pitch, investor deck, or business proposal
- general_notes: Any other document that doesn't fit above

Respond with ONLY the category name, nothing else.

Document:
{content}"""

# =============================================================================
# Document-Specific Extraction Prompts
# =============================================================================

EXTRACTION_PROMPTS = {
    "resume": """Extract facts from this RESUME for coaching purposes.

**Extract these categories:**
1. **Work Experience** - Each role with company, title, dates, team size
2. **Project Accomplishments** - EACH bullet point as a separate fact with metrics
   - What was built/done
   - Quantifiable impact (%, $, users, time saved)
   - Technologies used
3. **Skills** - Technical and soft skills mentioned
4. **Education** - Degrees, schools, certifications
5. **Leadership** - Team management, mentorship, cross-functional work

**Rules:**
- Extract EVERY accomplishment bullet as its own fact
- Include ALL numbers and metrics
- One fact = one complete standalone sentence

**Examples:**
- "Works as Software Engineer II at Microsoft since Oct 2022"
- "Built a feature for Outlook that increased user efficiency by 20%"
- "Led team of 5 engineers to reduce app load time by 40%"
- "Skilled in C++, Java, Python, and .NET framework"

Resume:
{content}""",

    "job_description": """Extract facts from this JOB DESCRIPTION.

**Extract these categories:**
1. **Role Info** - Title, company, team, level
2. **Responsibilities** - Each key responsibility as a fact
3. **Required Qualifications** - Must-have skills, years of experience
4. **Preferred Qualifications** - Nice-to-have skills
5. **Technical Requirements** - Specific technologies, tools, frameworks

**Rules:**
- Extract each requirement separately
- Note if something is required vs preferred
- Include specific numbers (years, team size, etc.)

**Examples:**
- "Requires 8+ years of software engineering experience"
- "Must have experience with distributed systems"
- "Preferred: Experience at a major cloud provider"
- "Role involves leading cross-org initiatives with 50+ engineers"

Job Description:
{content}""",

    "meeting_notes": """Extract facts from these MEETING NOTES for coaching.

**Extract these categories:**
1. **Decisions Made** - Any decisions or conclusions reached
2. **Action Items** - Tasks assigned, with owners if mentioned
3. **Feedback Received** - Any feedback given to/about the person
4. **Accomplishments Discussed** - Projects or wins mentioned
5. **Challenges/Blockers** - Problems or difficulties raised
6. **Goals/Plans** - Future plans or objectives discussed

**Rules:**
- Focus on facts relevant to the person's career/growth
- Include context (who said what, when, about what project)
- Note any commitments or deadlines

**Examples:**
- "Received positive feedback on the payment system launch"
- "Action item: Complete the design doc by Friday"
- "Discussed promotion timeline - targeting Q2"
- "Manager suggested improving stakeholder communication"

Meeting Notes:
{content}""",

    "performance_review": """Extract facts from this PERFORMANCE REVIEW.

**Extract these categories:**
1. **Strengths** - Positive feedback, things done well
2. **Accomplishments** - Specific achievements mentioned with impact
3. **Growth Areas** - Areas for improvement, constructive feedback
4. **Goals** - Objectives set for next period
5. **Ratings/Assessments** - Any scores or ratings given
6. **Peer Feedback** - Comments from colleagues

**Rules:**
- Extract both positive and constructive feedback
- Include specific examples mentioned
- Note who gave the feedback if specified

**Examples:**
- "Exceeded expectations on technical delivery"
- "Successfully led the migration project saving $2M annually"
- "Growth area: Need to delegate more instead of doing everything"
- "Peer feedback: Great at explaining complex concepts"

Performance Review:
{content}""",

    "project_document": """Extract facts from this PROJECT DOCUMENT.

**Extract these categories:**
1. **Project Overview** - What the project is, its goals
2. **Person's Role** - Their contribution, ownership areas
3. **Technical Details** - Architecture, technologies, scale
4. **Impact/Results** - Metrics, outcomes, business value
5. **Challenges Solved** - Technical or organizational problems addressed
6. **Timeline/Milestones** - Key dates, phases, deadlines

**Rules:**
- Focus on facts about the person's involvement
- Include technical specifics and scale
- Note any leadership or ownership

**Examples:**
- "Led the architecture design for the real-time processing system"
- "System handles 1M requests per second with 99.99% uptime"
- "Solved the data consistency problem using event sourcing"
- "Project launched in Q3, serving 50M users"

Project Document:
{content}""",

    "pitch_deck": """Extract facts from this PITCH DECK for founder coaching.

**Extract these categories:**
1. **Problem** - The problem being solved
2. **Solution** - The product/service offered
3. **Market** - Market size, target customers
4. **Traction** - Users, revenue, growth metrics
5. **Team** - Founder background, team experience
6. **Business Model** - How they make money
7. **Ask** - Funding amount, use of funds

**Rules:**
- Include all metrics and numbers
- Extract each key point separately
- Note the stage of the company

**Examples:**
- "Solving the problem of interview preparation for job seekers"
- "Target market is 10M professionals changing jobs annually"
- "Currently at $50K MRR with 200% month-over-month growth"
- "Founder previously led engineering at Stripe"

Pitch Deck:
{content}""",

    "general_notes": """Extract facts from this document for coaching purposes.

**Extract any information relevant to:**
1. **Professional Background** - Experience, skills, roles
2. **Accomplishments** - Things achieved with impact
3. **Goals & Interests** - What they want to achieve
4. **Challenges** - Difficulties or growth areas
5. **Ideas** - Startup ideas, project ideas, interests

**Rules:**
- Focus on career-relevant information
- Include specifics and metrics when available
- One fact per sentence

Document:
{content}""",
}

# =============================================================================
# Session Summary Extraction Prompts (Mode-Specific)
# =============================================================================

SESSION_SUMMARY_PROMPTS = {
    "interview": """Extract coaching insights from this MOCK INTERVIEW session.

**Context provided:**
- Session date: {session_date}
- BQ Category: {bq_category}
- Target company: {target_company}
- Target level: {target_level}
- Evaluation decision: {evaluation_decision}

**Extract these categories:**
1. **Session Context** - What was practiced (one fact)
2. **Strengths Demonstrated** - What user did well with SPECIFIC examples from transcript
   - Good STAR structure usage
   - Strong metrics/impact cited
   - Clear ownership language ("I led", "I decided")
   - Good follow-up handling
3. **Areas to Improve** - What needs work with SPECIFIC examples
   - Rambling or vague setup
   - Missing metrics or impact
   - Weak ownership ("we" instead of "I")
   - Poor time management in response
   - Filler words or hedging language
4. **Specific Feedback Given** - Key coaching tips from the session
5. **Recommended Focus** - What to practice next time

**Rules:**
- Be SPECIFIC - cite actual phrases or patterns from the transcript
- Focus on actionable insights that help future sessions
- Include the evaluation outcome as context
- One fact = one complete standalone insight

**Examples:**
- "Practiced leadership BQ for Google L5 on Jan 15 - evaluation: leaning hire"
- "Strength: Used strong metrics - 'reduced latency by 40%' and 'saved $2M annually'"
- "Strength: Clear ownership - consistently said 'I led' and 'I decided to'"
- "Improvement needed: Situation setup too long (2+ min) - keep to 30 seconds"
- "Improvement needed: Used 'we' 12 times vs 'I' 3 times - needs more ownership"
- "Tip given: Start responses with 'The situation was X. I decided to Y because Z.'"
- "Focus next session: Practice concise setups and quantifying personal impact"

Session Transcript + Evaluation:
{content}""",

    "career_1on1": """Extract coaching insights from this 1:1 MANAGER CONVERSATION practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: 1:1 with manager
- Key topics discussed: {topics}

**Extract these categories:**
1. **Session Context** - What scenario was practiced
2. **Power Dynamics Handled Well** - Where user showed strength
   - Held ground on important points
   - Asked clarifying questions
   - Used specific language
3. **Missed Opportunities** - Where user could have done better
   - Accepted vague feedback without pushing back
   - Over-explained or got defensive
   - Missed manipulation tactics
4. **Tactics Encountered** - What the "manager" threw at them
5. **Effective Responses Used** - Good counter-moves
6. **Recommended Focus** - What to practice next

**Examples:**
- "Practiced 1:1 where manager gave vague 'needs more impact' feedback"
- "Strength: Asked 'Can you give a specific example?' when feedback was vague"
- "Strength: Used declarative language - 'Here's what I need' not 'I was hoping'"
- "Missed: Accepted 'we'll discuss later' without setting specific follow-up date"
- "Tactic faced: Manager used 'everyone agrees you need to improve' (invisible consensus)"
- "Good response: 'Which specific concerns did they raise?' to counter hidden authority"
- "Focus next: Practice responses to scope creep and moving goalposts"

Session Transcript:
{content}""",

    "career_promotion": """Extract coaching insights from this PROMOTION CONVERSATION practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: Promotion discussion
- Target level: {target_level}

**Extract these categories:**
1. **Session Context** - Promotion scenario practiced
2. **Self-Advocacy Strengths** - Where user made strong case
   - Cited specific accomplishments with metrics
   - Connected impact to business value
   - Showed awareness of next-level expectations
3. **Gaps in Advocacy** - Where case was weak
   - Vague on impact or scope
   - Didn't address known gaps proactively
   - Accepted pushback too easily
4. **Objections Faced** - What resistance came up
5. **Counter-Moves Used** - How user responded to pushback
6. **Recommended Focus** - What to strengthen

**Examples:**
- "Practiced promotion conversation for Senior → Staff level"
- "Strength: Led with specific impact - 'I led the migration saving $2M annually'"
- "Strength: Proactively addressed gap - 'I know visibility is an area, here's my plan'"
- "Gap: When told 'not ready yet', didn't ask for specific criteria"
- "Objection faced: 'You need more cross-org influence' without examples"
- "Good counter: Asked 'What would demonstrating that look like in the next 6 months?'"
- "Focus next: Prepare 3 concrete examples of cross-org impact"

Session Transcript:
{content}""",

    "career_negotiation": """Extract coaching insights from this SALARY/OFFER NEGOTIATION practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: Compensation negotiation
- Context: {negotiation_context}

**Extract these categories:**
1. **Session Context** - Negotiation scenario practiced
2. **Strong Negotiation Moves** - What worked well
   - Anchored with market data
   - Used silence effectively
   - Asked about full package (RSUs, sign-on, etc.)
   - Didn't accept first offer
3. **Negotiation Weaknesses** - What needs work
   - Revealed salary expectations too early
   - Accepted artificial urgency
   - Didn't counter or countered too low
   - Got emotional or defensive
4. **Tactics Encountered** - Pressure tactics used
5. **Counter-Moves Used** - How user responded
6. **Recommended Focus** - What to practice

**Examples:**
- "Practiced new offer negotiation - initial offer $180K, target $210K"
- "Strength: Used precise number ($207,500) signaling research"
- "Strength: Asked about full package - RSUs, sign-on, start date flexibility"
- "Weakness: Said 'I'm currently at $170K' - revealed anchor too early"
- "Weakness: When told 'offer expires Friday', didn't push back on timeline"
- "Tactic faced: Recruiter used 'this is our best offer' (false finality)"
- "Good counter: 'I appreciate that. Let me discuss with my family and get back to you'"
- "Focus next: Practice deflecting salary history questions"

Session Transcript:
{content}""",

    "career_feedback": """Extract coaching insights from this GIVING FEEDBACK practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: Giving difficult feedback
- Scenario: {feedback_scenario}

**Extract these categories:**
1. **Session Context** - Feedback scenario practiced
2. **Feedback Delivery Strengths** - What worked
   - Used SBI framework (Situation-Behavior-Impact)
   - Stayed specific and factual
   - Maintained calm tone
   - Set clear expectations
3. **Delivery Weaknesses** - What needs work
   - Got defensive when challenged
   - Was too vague or softened too much
   - Didn't set clear next steps
   - Let conversation get derailed
4. **Recipient Reactions Handled** - Defensive moves encountered
5. **Effective Redirects** - How user stayed on track
6. **Recommended Focus** - What to improve

**Examples:**
- "Practiced giving feedback to report who shipped buggy code without review"
- "Strength: Used SBI - 'In Tuesday's deploy, code went out without review, causing 2hr outage'"
- "Strength: Stayed calm when report got defensive - 'Let's focus on the process'"
- "Weakness: Accepted 'everyone does it' without redirecting to the specific issue"
- "Weakness: Ended without clear expectations for next time"
- "Reaction handled: Report tried DARVO - 'You never gave me clear guidelines'"
- "Good redirect: 'We can discuss guidelines separately. Right now I need us to address this incident'"
- "Focus next: Practice setting specific expectations and follow-up commitments"

Session Transcript:
{content}""",

    "career_conflict": """Extract coaching insights from this CONFLICT RESOLUTION practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: Workplace conflict
- Scenario: {conflict_scenario}

**Extract these categories:**
1. **Session Context** - Conflict scenario practiced
2. **De-escalation Strengths** - What worked
   - Stayed calm and professional
   - Focused on issues not personalities
   - Sought to understand other perspective
   - Proposed solutions
3. **Escalation Risks** - Where user could have made it worse
   - Got defensive or accusatory
   - Brought up past grievances
   - Used absolute language ("you always", "you never")
4. **Conflict Tactics Faced** - What the other party did
5. **Effective Responses** - Good moves by user
6. **Recommended Focus** - What to practice

**Examples:**
- "Practiced conflict with peer who publicly criticized design doc"
- "Strength: Opened with curiosity - 'I'd like to understand your concerns about the design'"
- "Strength: Stayed factual - 'The review comments raised X and Y. Let's discuss those'"
- "Risk: Said 'you always do this' - escalated unnecessarily"
- "Risk: Brought up unrelated past incident"
- "Tactic faced: Peer tried triangulation - 'Everyone on the team agrees with me'"
- "Good response: 'I'd prefer we discuss this directly. What specific concerns do you have?'"
- "Focus next: Practice responding to public criticism without getting defensive"

Session Transcript:
{content}""",

    "networking": """Extract coaching insights from this NETWORKING practice.

**Context provided:**
- Session date: {session_date}
- Conversation type: Networking/social
- Context: {networking_context}

**Extract these categories:**
1. **Session Context** - Networking scenario practiced
2. **Connection Strengths** - What built rapport
   - Asked good follow-up questions
   - Found common ground
   - Shared authentically
   - Good energy and engagement
3. **Connection Gaps** - What hurt rapport
   - Talked too much about self
   - Missed opportunities to connect
   - Gave conversation-killing responses
   - Seemed distracted or uninterested
4. **Frameworks Used Well** - AIR, FORD, AAA application
5. **Missed Opportunities** - Where to deepen
6. **Recommended Focus** - What to practice

**Examples:**
- "Practiced networking at tech conference scenario"
- "Strength: Used FORD well - discovered shared interest in hiking"
- "Strength: Good follow-up question - 'What got you interested in that area?'"
- "Gap: When they mentioned job stress, changed subject instead of empathizing"
- "Gap: Gave one-word answer to 'What do you do?' - killed momentum"
- "Framework used: AAA (Affirm-Add-Ask) to keep conversation flowing"
- "Missed: Could have offered to connect them with someone in their target field"
- "Focus next: Practice responding to personal disclosures with empathy"

Session Transcript:
{content}""",
}


class MemoryService:
    """
    Service for managing user memories using Mem0.

    Usage:
        service = MemoryService()

        # Add memories from resume
        service.add_document(user_id, resume_text, source_type="resume")

        # Search relevant memories for interview
        memories = service.search(user_id, "Tell me about a time you led a team")
    """

    def __init__(self):
        """Initialize Mem0 with Qdrant Cloud and OpenAI client."""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Use a history DB path inside the project data dir to avoid
        # macOS com.apple.provenance quarantine on ~/.mem0/history.db
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        history_db_dir = os.path.join(project_root, "data")
        os.makedirs(history_db_dir, exist_ok=True)
        history_db_path = os.path.join(history_db_dir, "mem0_history.db")

        config = {
            "version": "v1.1",
            "history_db_path": history_db_path,
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "coach_ai_memories",
                    "url": os.getenv("QDRANT_URL"),
                    "api_key": os.getenv("QDRANT_API_KEY"),
                }
            },
            "llm": {
                "provider": "openai",
                "config": {
                    "model": "gpt-4o-mini",
                    "temperature": 0.1,
                    "api_key": os.getenv("OPENAI_API_KEY"),
                }
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "text-embedding-3-small",
                    "api_key": os.getenv("OPENAI_API_KEY"),
                }
            }
        }

        self.memory = Memory.from_config(config)

    def classify_document(self, content: str) -> str:
        """
        Step 1: Classify document type.

        Args:
            content: Document text content

        Returns:
            Document type string (e.g., "resume", "job_description", etc.)
        """
        # Truncate content for classification (first 2000 chars is enough)
        truncated = content[:2000] if len(content) > 2000 else content

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": CLASSIFICATION_PROMPT.format(content=truncated)}
            ],
            temperature=0,
            max_tokens=20,
        )

        doc_type = response.choices[0].message.content.strip().lower()

        # Validate and fallback
        if doc_type not in DOCUMENT_TYPES:
            doc_type = "general_notes"

        return doc_type

    def extract_facts(self, content: str, doc_type: str) -> List[str]:
        """
        Step 2: Extract facts using document-specific prompt.

        Args:
            content: Document text content
            doc_type: Document type from classification

        Returns:
            List of extracted facts
        """
        prompt_template = EXTRACTION_PROMPTS.get(doc_type, EXTRACTION_PROMPTS["general_notes"])
        prompt = prompt_template.format(content=content)

        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You extract facts as requested. Output each fact on a new line. Do not number them or use bullet points."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        facts_text = response.choices[0].message.content.strip()

        # Split into individual facts and clean up
        facts = []
        for line in facts_text.split("\n"):
            line = line.strip()
            # Remove common prefixes
            line = line.lstrip("-•*123456789. ")
            if line and len(line) > 10:  # Skip empty or too short lines
                facts.append(line)

        return facts

    def add_document(
        self,
        user_id: str,
        content: str,
        source_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract and store memories from a document using two-step process:
        1. Classify document type (or use provided source_type)
        2. Extract facts using document-specific prompt
        3. Store each fact as a memory

        Args:
            user_id: Firebase user ID
            content: Document text content
            source_type: Optional override for document type (auto-detected if not provided)
            filename: Original filename for reference

        Returns:
            Dict with extraction results including count of memories added
        """
        # Step 1: Classify document type (or use provided)
        if source_type and source_type in DOCUMENT_TYPES:
            doc_type = source_type
        else:
            doc_type = self.classify_document(content)

        # Step 2: Extract facts using document-specific prompt
        facts = self.extract_facts(content, doc_type)

        # Step 3: Store each fact as a memory
        memories_added = 0
        for fact in facts:
            metadata = {
                "source_type": doc_type,
            }
            if filename:
                metadata["filename"] = filename

            try:
                self.memory.add(
                    fact,
                    user_id=user_id,
                    metadata=metadata,
                )
                memories_added += 1
            except Exception as e:
                # Log but continue with other facts
                print(f"Warning: Failed to add memory: {e}")

        return {
            "success": True,
            "memories_added": memories_added,
            "document_type": doc_type,
            "facts_extracted": len(facts),
            "source_type": doc_type,
        }

    def add_resume(self, user_id: str, content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Add memories from a resume."""
        return self.add_document(user_id, content, source_type="resume", filename=filename)

    def add_job_description(self, user_id: str, content: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """Add memories from a job description."""
        return self.add_document(user_id, content, source_type="job_description", filename=filename)

    def add_conversation(self, user_id: str, content: str) -> Dict[str, Any]:
        """Add memories from a conversation (for learning over time)."""
        return self.add_document(user_id, content, source_type="conversation")

    def add_session_summary(
        self,
        user_id: str,
        transcript: str,
        mode: str,
        session_id: str,
        session_date: str,
        evaluation: Optional[str] = None,
        evaluation_decision: Optional[str] = None,
        bq_category: Optional[str] = None,
        target_company: Optional[str] = None,
        target_level: Optional[str] = None,
        conversation_type: Optional[str] = None,
        scenario: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract and store insights from a coaching session.
        Uses mode-specific extraction prompts for targeted insights.

        Args:
            user_id: Firebase user ID
            transcript: Full session transcript (user + AI messages)
            mode: Session mode - "interview", "career", "networking"
            session_id: Unique session identifier
            session_date: ISO date string (e.g., "2025-01-22")
            evaluation: Optional evaluation markdown (for interview mode)
            evaluation_decision: Optional hire decision (for interview mode)
            bq_category: BQ category practiced (for interview mode)
            target_company: Target company (for interview mode)
            target_level: Target level (for interview/promotion)
            conversation_type: Career conversation type (1on1, promotion, etc.)
            scenario: Scenario description

        Returns:
            Dict with extraction results
        """
        # Determine which prompt to use based on mode and conversation_type
        if mode == "interview":
            prompt_key = "interview"
        elif mode == "career":
            # Map career conversation types to specific prompts
            career_prompt_map = {
                "1on1": "career_1on1",
                "promotion": "career_promotion",
                "negotiation": "career_negotiation",
                "feedback": "career_feedback",
                "conflict": "career_conflict",
            }
            prompt_key = career_prompt_map.get(conversation_type, "career_1on1")
        elif mode == "networking":
            prompt_key = "networking"
        else:
            # Fallback to interview-style extraction for unknown modes
            prompt_key = "interview"

        prompt_template = SESSION_SUMMARY_PROMPTS.get(prompt_key)
        if not prompt_template:
            print(f"⚠️ No session summary prompt for mode: {mode}/{conversation_type}")
            return {"success": False, "memories_added": 0, "error": "Unknown mode"}

        # Build content with evaluation if provided
        content = transcript
        if evaluation:
            content += f"\n\n--- EVALUATION ---\n{evaluation}"

        # Format prompt with context variables
        # Use safe defaults for missing values
        prompt = prompt_template.format(
            content=content,
            session_date=session_date or "unknown",
            bq_category=bq_category or "general",
            target_company=target_company or "unknown company",
            target_level=target_level or "unknown level",
            evaluation_decision=evaluation_decision or "not evaluated",
            topics=scenario or "general discussion",
            negotiation_context=scenario or "compensation discussion",
            feedback_scenario=scenario or "giving feedback",
            conflict_scenario=scenario or "workplace conflict",
            networking_context=scenario or "professional networking",
        )

        # Extract insights using GPT-4o-mini
        response = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You extract coaching insights from practice sessions. Output each insight on a new line. Be specific - cite actual phrases or patterns. Focus on actionable insights for future improvement."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        facts_text = response.choices[0].message.content.strip()

        # Parse facts
        facts = []
        for line in facts_text.split("\n"):
            line = line.strip()
            line = line.lstrip("-•*123456789. ")
            if line and len(line) > 10:
                facts.append(line)

        # Store each fact with session metadata
        memories_added = 0
        source_type = f"session_{mode}" if mode != "career" else f"session_career_{conversation_type or '1on1'}"

        for fact in facts:
            metadata = {
                "source_type": source_type,
                "session_id": session_id,
                "session_date": session_date,
                "mode": mode,
            }
            # Add optional metadata
            if bq_category:
                metadata["bq_category"] = bq_category
            if target_company:
                metadata["target_company"] = target_company
            if target_level:
                metadata["target_level"] = target_level
            if conversation_type:
                metadata["conversation_type"] = conversation_type
            if evaluation_decision:
                metadata["evaluation_decision"] = evaluation_decision

            try:
                self.memory.add(
                    fact,
                    user_id=user_id,
                    metadata=metadata,
                )
                memories_added += 1
            except Exception as e:
                print(f"Warning: Failed to add session memory: {e}")

        print(f"🧠 Extracted {memories_added} insights from {mode} session for user {user_id[:8]}...")

        return {
            "success": True,
            "memories_added": memories_added,
            "facts_extracted": len(facts),
            "source_type": source_type,
            "session_id": session_id,
        }

    def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant memories.

        Args:
            user_id: Firebase user ID
            query: Search query (e.g., interview question, topic)
            limit: Max number of memories to return

        Returns:
            List of relevant memories with scores
        """
        results = self.memory.search(
            query=query,
            user_id=user_id,
            limit=limit,
        )

        memories = []
        for r in results.get("results", []):
            memories.append({
                "memory": r.get("memory", ""),
                "score": r.get("score", 0.0),
                "metadata": r.get("metadata", {}),
            })

        return memories

    def search_for_interview(
        self,
        user_id: str,
        question: str,
        limit: int = 5,
    ) -> str:
        """
        Search memories and format for injection into interview prompt.
        Groups facts by source type so the AI knows what's resume vs JD vs other.

        Args:
            user_id: Firebase user ID
            question: The BQ question being asked
            limit: Max memories to include

        Returns:
            Formatted string of relevant memories for prompt injection
        """
        memories = self.search(user_id, question, limit=limit)

        if not memories:
            return ""

        # Group by source type
        by_type: Dict[str, List[str]] = {}
        for mem in memories:
            source_type = mem.get("metadata", {}).get("source_type", "general")
            fact = mem.get("memory", "")
            if fact:
                if source_type not in by_type:
                    by_type[source_type] = []
                by_type[source_type].append(fact)

        # Format with clear labels for each source type
        type_labels = {
            # Document types
            "resume": "FROM USER'S RESUME (their past/current experience)",
            "job_description": "FROM TARGET JOB DESCRIPTION (where they're interviewing)",
            "meeting_notes": "FROM MEETING NOTES",
            "performance_review": "FROM PERFORMANCE REVIEW",
            "project_document": "FROM PROJECT DOCUMENTS",
            "pitch_deck": "FROM PITCH DECK",
            "general_notes": "FROM USER'S NOTES",
            # Session summary types
            "session_interview": "FROM PAST INTERVIEW PRACTICE (strengths & areas to improve)",
            "session_career_1on1": "FROM PAST 1:1 PRACTICE (manager conversation insights)",
            "session_career_promotion": "FROM PAST PROMOTION PRACTICE (self-advocacy insights)",
            "session_career_negotiation": "FROM PAST NEGOTIATION PRACTICE (tactics & responses)",
            "session_career_feedback": "FROM PAST FEEDBACK PRACTICE (delivery insights)",
            "session_career_conflict": "FROM PAST CONFLICT PRACTICE (de-escalation insights)",
            "session_networking": "FROM PAST NETWORKING PRACTICE (connection insights)",
        }

        lines = []
        for source_type, facts in by_type.items():
            label = type_labels.get(source_type, f"FROM {source_type.upper()}")
            lines.append(f"\n### {label}")
            for fact in facts:
                lines.append(f"- {fact}")

        return "\n".join(lines)

    @staticmethod
    def format_memories_by_type(memories: List[Dict[str, Any]]) -> str:
        """
        Format a list of memories grouped by source type.
        Use this when you have raw memory results from search().

        Args:
            memories: List of memory dicts with 'memory' and 'metadata' keys

        Returns:
            Formatted string with facts grouped by source type
        """
        if not memories:
            return ""

        # Group by source type
        by_type: Dict[str, List[str]] = {}
        for mem in memories:
            source_type = mem.get("metadata", {}).get("source_type", "general")
            fact = mem.get("memory", "")
            if fact:
                if source_type not in by_type:
                    by_type[source_type] = []
                by_type[source_type].append(fact)

        # Format with clear labels for each source type
        type_labels = {
            # Document types
            "resume": "FROM USER'S RESUME (their past/current experience)",
            "job_description": "FROM TARGET JOB DESCRIPTION (where they're interviewing)",
            "meeting_notes": "FROM MEETING NOTES",
            "performance_review": "FROM PERFORMANCE REVIEW",
            "project_document": "FROM PROJECT DOCUMENTS",
            "pitch_deck": "FROM PITCH DECK",
            "general_notes": "FROM USER'S NOTES",
            # Session summary types
            "session_interview": "FROM PAST INTERVIEW PRACTICE (strengths & areas to improve)",
            "session_career_1on1": "FROM PAST 1:1 PRACTICE (manager conversation insights)",
            "session_career_promotion": "FROM PAST PROMOTION PRACTICE (self-advocacy insights)",
            "session_career_negotiation": "FROM PAST NEGOTIATION PRACTICE (tactics & responses)",
            "session_career_feedback": "FROM PAST FEEDBACK PRACTICE (delivery insights)",
            "session_career_conflict": "FROM PAST CONFLICT PRACTICE (de-escalation insights)",
            "session_networking": "FROM PAST NETWORKING PRACTICE (connection insights)",
        }

        lines = []
        for source_type, facts in by_type.items():
            label = type_labels.get(source_type, f"FROM {source_type.upper()}")
            lines.append(f"\n### {label}")
            for fact in facts:
                lines.append(f"- {fact}")

        return "\n".join(lines)

    def get_all(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all memories for a user."""
        results = self.memory.get_all(user_id=user_id)
        # Mem0 returns "results" not "memories"
        return results.get("results", [])

    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory by ID."""
        try:
            self.memory.delete(memory_id)
            return True
        except Exception:
            return False

    def clear_user_memories(self, user_id: str) -> int:
        """
        Clear all memories for a user.

        Returns:
            Number of memories deleted
        """
        all_memories = self.get_all(user_id)
        count = 0
        for mem in all_memories:
            if self.delete_memory(mem["id"]):
                count += 1
        return count

    def get_user_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of user's stored memories.

        Returns:
            Dict with counts by source type
        """
        all_memories = self.get_all(user_id)

        summary = {
            "total": len(all_memories),
            "by_source": {},
        }

        for mem in all_memories:
            source = mem.get("metadata", {}).get("source_type", "unknown")
            summary["by_source"][source] = summary["by_source"].get(source, 0) + 1

        return summary


def get_memory_service() -> MemoryService:
    """Get singleton instance of MemoryService."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
