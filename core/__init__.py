# Core abstractions for Coach AI
from .llm_client import LLMClient, llm_client, LLMResponse, ModelType
from .auth import AuthenticatedUser, get_current_user, get_optional_user
from .memory import get_memory_context, get_memory_context_for_prompt, MemoryContext
from .artifacts import (
    ArtifactContext,
    ArtifactResult,
    generate_artifact,
    generate_artifact_streaming,
)
from .models import (
    CandidateLevel,
    CapabilityMode,
    SourceType,
    Rating,
    Source,
    ResumeMetadata,
    JobDescriptionMetadata,
    Message,
    ChatMessageRequest,
    ChatIntroRequest,
    AnalyzeSourceRequest,
    SummarizeRequest,
    SessionNotesRequest,
    GenerateArtifactRequest,
    BQAnalysisRequest,
    SourceAnalysisResponse,
    ChatResponse,
    EvaluationResponse,
    ArtifactResponse,
    CoachPersona,
)

__all__ = [
    # LLM
    'LLMClient', 'llm_client', 'LLMResponse', 'ModelType',
    # Auth
    'AuthenticatedUser', 'get_current_user', 'get_optional_user',
    # Memory
    'get_memory_context', 'get_memory_context_for_prompt', 'MemoryContext',
    # Artifacts
    'ArtifactContext', 'ArtifactResult',
    'generate_artifact', 'generate_artifact_streaming',
    # Models
    'CandidateLevel', 'CapabilityMode', 'SourceType', 'Rating',
    'Source', 'ResumeMetadata', 'JobDescriptionMetadata', 'Message',
    'ChatMessageRequest', 'ChatIntroRequest', 'AnalyzeSourceRequest',
    'SummarizeRequest', 'SessionNotesRequest', 'GenerateArtifactRequest',
    'BQAnalysisRequest', 'SourceAnalysisResponse', 'ChatResponse',
    'EvaluationResponse', 'ArtifactResponse', 'CoachPersona',
]
