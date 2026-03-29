"""
Mem0 Memory Module

Provides long-term memory capabilities using Mem0 + Qdrant.
Extracts atomic facts from user documents (resume, JD) and enables
semantic retrieval for personalized coaching.

Note: Named mem0_memory to avoid conflict with existing core/memory.py
"""

from .service import MemoryService, get_memory_service

__all__ = ["MemoryService", "get_memory_service"]
