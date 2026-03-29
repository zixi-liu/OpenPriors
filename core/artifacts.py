"""
Universal Artifact Generator

Uses LLM reasoning to determine what to write based on conversation context.
No hardcoded artifact types - the model reasons about format and structure.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, AsyncGenerator

from .llm_client import llm_client, ModelType

# Use Gemini 3 Pro for artifact generation (best reasoning for document generation)
ARTIFACT_MODEL = ModelType.GEMINI_3_PRO.value


@dataclass
class ArtifactContext:
    """Context for artifact generation."""
    messages: List[Dict[str, str]] = field(default_factory=list)
    persona_name: str = "Coach"
    capability: Optional[str] = None
    level: str = "Senior"
    sources: List[Dict] = field(default_factory=list)
    title: Optional[str] = None


@dataclass
class ArtifactResult:
    """Result of artifact generation."""
    content: str
    title: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _build_universal_prompt(context: ArtifactContext) -> str:
    """Build the universal reasoning prompt for artifact generation."""

    # Format conversation history
    conversation = "\n\n".join([
        f"**{m.get('role', 'user').upper()}**: {m.get('content', '')}"
        for m in context.messages[-20:]  # Last 20 messages for context
    ])

    # Format sources if available
    sources_text = ""
    if context.sources:
        active_sources = [s for s in context.sources if s.get('isActive', True)]
        for s in active_sources[:3]:
            sources_text += f"\n\n--- {s.get('title', 'Document')} ---\n{s.get('content', '')[:2000]}"

    # Capability context
    capability_hint = ""
    if context.capability:
        capability_hint = f"\nThe user is in '{context.capability}' mode."

    return f"""You are a professional document generator. Analyze the conversation and generate the appropriate document.

## CONVERSATION
{conversation}

## USER'S MATERIALS
{sources_text if sources_text else 'None'}

## CONTEXT
- Persona: {context.persona_name}
- Level: {context.level}{capability_hint}

## TASK

Generate a polished document based on what the user discussed and asked for.

**Formatting requirements:**
- Start with: # [Descriptive Title]
- Use **bold** for section headers and key terms
- Use ## for major sections
- Use bullet points (- ) for lists
- Use clear paragraph breaks
- Highlight metrics and numbers with **bold**

**Content guidelines:**
- Use the structure that best fits the content
- Extract specific details, metrics, and examples from the conversation
- Be concise but impactful
- Use professional language

Generate now:"""


async def generate_artifact_streaming(
    context: ArtifactContext,
) -> AsyncGenerator[str, None]:
    """
    Generate artifact with streaming output.
    Yields chunks of content as they're generated.
    """
    prompt = _build_universal_prompt(context)

    async for chunk in llm_client.stream(
        prompt=prompt,
        model=ARTIFACT_MODEL,
        temperature=0.7,
        max_tokens=4000
    ):
        yield chunk


async def generate_artifact(
    context: ArtifactContext,
) -> ArtifactResult:
    """
    Generate artifact (non-streaming).
    Returns complete result.
    """
    prompt = _build_universal_prompt(context)

    response = await llm_client.complete(
        prompt=prompt,
        model=ARTIFACT_MODEL,
        temperature=0.7,
        max_tokens=4000
    )

    content = response.content

    # Extract title from first heading
    title = None
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line.replace('# ', '').strip()
            break
    title = title or context.title or "Generated Document"

    return ArtifactResult(
        content=content,
        title=title,
        metadata={
            "model": response.model,
            "usage": response.usage
        }
    )
