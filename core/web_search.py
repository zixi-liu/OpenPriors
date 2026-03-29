"""
Web Search Utilities for Company Research

Uses Gemini with grounding (Google Search) to get company information
when deep research data is not available.

This is a lightweight fallback for companies we haven't pre-researched.
Works for ANY role (not just engineering) - tailored to the specific position.
"""

import os
from typing import Optional

# LLM Client
from core.llm_client import llm_client, ModelType


async def search_company_info(
    company: str,
    role: str = "Professional",
    level: str = "Senior",
    jd_summary: Optional[str] = None,
) -> str:
    """
    Search for company information using Gemini with Google Search grounding.

    This is used as a fallback when we don't have deep research data for a company.
    Returns a condensed summary suitable for interview prep.

    Works for ANY role - not just engineering. The search is tailored to the specific
    role and level the user is applying for.

    Args:
        company: Company name
        role: Target role (e.g., "Product Manager", "Data Scientist", "Marketing Manager", "Software Engineer")
        level: Target level (e.g., "Senior", "Director", "VP")
        jd_summary: Optional - key points from the job description to focus the search

    Returns:
        Formatted company info string for use in prompts
    """
    print(f"🌐 Searching for {company} {level} {role} interview info...")

    # Build role-specific context
    jd_context = ""
    if jd_summary:
        jd_context = f"""
The job description emphasizes these key requirements:
{jd_summary}

Focus your search on information relevant to these specific requirements.
"""

    # Build search-optimized prompt - role agnostic
    search_prompt = f"""Search for information about {company} to help someone prepare for a {level} {role} interview.

{jd_context}

I need to know:

1. **Company Overview & Culture**
   - What is {company}'s mission and what are they known for?
   - What do they value in employees? (company values, culture)
   - Work environment (remote/hybrid/in-office, work-life balance reputation)

2. **{role}-Specific Context**
   - What does the {role} function look like at {company}?
   - How is the {role} team structured? Who do they work with?
   - What tools, methodologies, or frameworks do {role}s use at {company}?
   - What makes a successful {role} at {company}?

3. **Interview Process for {role}**
   - How many interview rounds for {role} positions?
   - What types of interviews? (behavioral, case study, technical, presentation, etc.)
   - Who typically conducts {role} interviews at {company}?
   - What competencies do they evaluate for {role}s?

4. **What {company} Looks For in {level} {role}s**
   - Key skills and experiences they value
   - Leadership expectations at {level} level
   - Common reasons candidates succeed or fail
   - Any known interview questions or themes for {role}s

5. **Recent News & Strategic Context (2024-2025)**
   - Recent company news, product launches, or strategic shifts
   - How might these affect the {role} function?
   - Growth areas or challenges the company is facing

Please search for recent (2024-2025) information about {company}, specifically related to {role} positions.

Return a concise, actionable summary. Focus on insights that would help a {level} {role} candidate prepare for behavioral interviews at {company}.
"""

    try:
        # Use Gemini with grounding for web search
        response = await llm_client.complete(
            prompt=search_prompt,
            model=ModelType.GEMINI_25_FLASH.value,
            temperature=0.3,
            max_tokens=2000  # More tokens for comprehensive role-specific info
        )

        result = response.content
        print(f"✅ Got {len(result)} chars of {role}-specific company info from web search")
        return result

    except Exception as e:
        print(f"❌ Web search failed: {e}")
        return f"""Limited information available about {company} for {role} positions.

General preparation tips for {level} {role} interviews:
- Research {company}'s products, services, and recent news
- Understand the company's mission and values
- Prepare STAR-format stories demonstrating relevant competencies
- Have specific examples of {role}-relevant achievements ready
- Research the team structure and who you might be working with
- Prepare thoughtful questions about the role and company direction
"""


async def search_role_requirements(
    company: str,
    role: str,
    level: str = "Senior",
    jd_context: Optional[str] = None,
) -> str:
    """
    Search for specific role requirements and job posting patterns.

    Args:
        company: Company name
        role: Target role (any role, not just engineering)
        level: Target level
        jd_context: Optional context from job description

    Returns:
        Summary of typical requirements and expectations for this specific role
    """
    jd_section = ""
    if jd_context:
        jd_section = f"""
The job description mentions these key areas:
{jd_context}

Focus on information relevant to these requirements.
"""

    search_prompt = f"""Search for {company} {level} {role} job requirements and interview expectations.

{jd_section}

Find information about:
1. Required skills and experience for {role}s at {company}
2. Behavioral competencies they evaluate (leadership, collaboration, problem-solving, etc.)
3. Common interview questions or case studies for {role} positions
4. What differentiates successful {role} candidates at {company}
5. Day-to-day responsibilities and expectations

Focus on {company}-specific information where available. If {company}-specific info is limited, provide industry-standard expectations for {level} {role} positions.
"""

    try:
        response = await llm_client.complete(
            prompt=search_prompt,
            model=ModelType.GEMINI_25_FLASH.value,
            temperature=0.3,
            max_tokens=1500
        )
        return response.content

    except Exception as e:
        print(f"❌ Role requirements search failed: {e}")
        return f"Standard {level} {role} expectations apply. Focus on demonstrating relevant skills and experience aligned with the job description."


async def extract_jd_key_points(jd_text: str) -> str:
    """
    Extract key points from a job description to focus web search.

    Args:
        jd_text: Full job description text

    Returns:
        Condensed key points (requirements, competencies, responsibilities)
    """
    if not jd_text or len(jd_text) < 100:
        return ""

    extract_prompt = f"""Extract the KEY requirements from this job description in a concise bullet list.

JOB DESCRIPTION:
{jd_text[:3000]}  # Limit to avoid token issues

Extract:
- Required skills/qualifications (top 5)
- Key responsibilities (top 3)
- Behavioral competencies mentioned
- Team/collaboration expectations
- Any specific tools, methodologies, or domain knowledge required

Return a brief bullet list (max 10 bullets). Focus on the MOST important requirements.
"""

    try:
        response = await llm_client.complete(
            prompt=extract_prompt,
            model=ModelType.GEMINI_25_FLASH.value,
            temperature=0.1,
            max_tokens=500
        )
        return response.content
    except Exception as e:
        print(f"⚠️ Could not extract JD key points: {e}")
        return ""


# Quick test
if __name__ == "__main__":
    import asyncio

    async def test():
        # Test with a non-engineering role
        result = await search_company_info(
            company="Airbnb",
            role="Product Manager",
            level="Senior"
        )
        print("=" * 60)
        print("RESULT (Product Manager):")
        print("=" * 60)
        print(result)

        print("\n\n")

        # Test with engineering role
        result2 = await search_company_info(
            company="Stripe",
            role="Software Engineer",
            level="Staff"
        )
        print("=" * 60)
        print("RESULT (Software Engineer):")
        print("=" * 60)
        print(result2)

    asyncio.run(test())
