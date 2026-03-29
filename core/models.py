"""
Pydantic Models for Coach AI

Centralized data models for request/response validation.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================
# Enums
# ============================================================

class CandidateLevel(str, Enum):
    """Candidate experience levels."""
    JUNIOR = "Junior"
    MID = "Mid"
    SENIOR = "Senior"
    STAFF = "Staff"
    PRINCIPAL = "Principal"


class CapabilityMode(str, Enum):
    """Available coaching capability modes."""
    MOCK_INTERVIEW = "mock_interview"
    CAREER_COACHING = "career_coaching"
    RESUME_REVIEW = "resume_review"
    STAR_STORIES = "star_stories"


class SourceType(str, Enum):
    """Types of source documents."""
    RESUME = "resume"
    JOB_DESCRIPTION = "job_description"
    DOCUMENT = "document"
    LINKEDIN = "linkedin"
    GITHUB = "github"


class Rating(str, Enum):
    """Interview rating scale."""
    STRONG_HIRE = "Strong Hire"
    HIRE = "Hire"
    LEANING_HIRE = "Leaning Hire"
    LEANING_NO_HIRE = "Leaning No Hire"
    NO_HIRE = "No Hire"


# ============================================================
# Source Documents
# ============================================================

class Source(BaseModel):
    """A source document (resume, JD, etc.)."""
    id: str
    name: str
    type: SourceType
    content: str = ""
    url: Optional[str] = None

    # Extracted metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResumeMetadata(BaseModel):
    """Extracted resume metadata."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    current_role: Optional[str] = None
    current_company: Optional[str] = None
    years_of_experience: Optional[int] = None
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    inferred_level: Optional[CandidateLevel] = None


class JobDescriptionMetadata(BaseModel):
    """Extracted job description metadata."""
    title: Optional[str] = None
    company: Optional[str] = None
    level: Optional[CandidateLevel] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    bq_categories: List[str] = Field(default_factory=list)


# ============================================================
# Chat Messages
# ============================================================

class Message(BaseModel):
    """A chat message."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: Optional[str] = None


# ============================================================
# API Requests
# ============================================================

class ChatMessageRequest(BaseModel):
    """Request for /api/chat/message endpoint."""
    message: str
    persona: Dict[str, Any]
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[Dict[str, str]] = Field(default_factory=list)
    capability: Optional[CapabilityMode] = None
    level: CandidateLevel = CandidateLevel.SENIOR
    bqCategory: Optional[str] = None
    memoryContext: str = ""
    # Company context - extracted from JD or user-selected
    company: Optional[str] = None  # e.g., "airbnb", "google", "meta"
    team: Optional[str] = None     # e.g., "payments", "search", "ads"


class ChatIntroRequest(BaseModel):
    """Request for /api/chat/intro endpoint."""
    persona: Dict[str, Any]
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    capability: Optional[CapabilityMode] = None


class AnalyzeSourceRequest(BaseModel):
    """Request for /api/analyze-source endpoint."""
    content: str
    filename: str


class SummarizeRequest(BaseModel):
    """Request for /api/chat/summarize endpoint."""
    messages: List[Dict[str, str]]
    personaName: str
    capability: Optional[CapabilityMode] = None


class SessionNotesRequest(BaseModel):
    """Request for /api/artifacts/session-notes endpoint."""
    messages: List[Dict[str, str]]
    personaName: str = "Coach"
    capability: Optional[CapabilityMode] = None
    title: Optional[str] = None


class GenerateArtifactRequest(BaseModel):
    """Request for /api/artifacts/generate endpoint."""
    messages: List[Dict[str, str]]
    userRequest: str
    personaName: str = "Coach"
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    capability: Optional[CapabilityMode] = None
    level: CandidateLevel = CandidateLevel.SENIOR


class BQAnalysisRequest(BaseModel):
    """Request for BQ analysis endpoints."""
    question: str
    answer: str
    level: CandidateLevel = CandidateLevel.SENIOR
    style: str = "real_interview"


# ============================================================
# API Responses
# ============================================================

class SourceAnalysisResponse(BaseModel):
    """Response from source analysis."""
    type: SourceType
    metadata: Dict[str, Any]
    summary: str


class ChatResponse(BaseModel):
    """Response from chat endpoints."""
    response: str
    artifact: Optional[Dict[str, Any]] = None


class EvaluationResponse(BaseModel):
    """Response from evaluation endpoints."""
    rating: Rating
    strengths: List[str]
    improvements: List[str]
    detailed_feedback: str
    score: Optional[int] = None


class ArtifactResponse(BaseModel):
    """Response from artifact generation."""
    success: bool
    content: str
    title: str
    artifact_type: str


# ============================================================
# Persona
# ============================================================

class PersonaVisual(BaseModel):
    """Visual settings for a persona."""
    icon: str = "🎯"
    iconColor: str = "#2563EB"
    backgroundColor: str = "#DBEAFE"
    avatarUrl: Optional[str] = None


class PersonaCommunicationStyle(BaseModel):
    """Communication style for a persona."""
    formality: str = "professional"
    verbosity: str = "balanced"
    questioningStyle: str = "direct"
    supportiveness: float = 0.7


class PersonaBackstory(BaseModel):
    """Backstory for a persona."""
    summary: str
    background: str = ""
    motivation: str = ""
    conversationStyle: str = ""
    interests: List[str] = Field(default_factory=list)
    quirks: List[str] = Field(default_factory=list)


class CoachPersona(BaseModel):
    """A coach persona configuration."""
    id: str
    displayName: str
    role: str
    focusAreas: List[str] = Field(default_factory=list)
    visual: PersonaVisual = Field(default_factory=PersonaVisual)
    personality: Dict[str, Any] = Field(default_factory=dict)
    expertise: List[str] = Field(default_factory=list)
    communicationStyle: PersonaCommunicationStyle = Field(default_factory=PersonaCommunicationStyle)
    backstory: PersonaBackstory
    mbti: str = "ENTJ"
    isCustom: bool = False
    knowledgeSourceUrl: Optional[str] = None
