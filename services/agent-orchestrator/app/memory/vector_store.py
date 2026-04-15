"""Vector memory store using Pinecone for long-term agent context.

Stores user preferences, past interactions, and learned patterns
for RAG-enhanced responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class MemoryEntry:
    """A single memory entry in the vector store."""

    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class VectorMemory:
    """In-memory vector store (Pinecone interface).

    In production, this connects to Pinecone for persistent
    vector storage and similarity search.
    """

    def __init__(self) -> None:
        # In-memory store for development
        self._memories: dict[str, MemoryEntry] = {}

    async def store(
        self,
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryEntry:
        """Store a new memory entry."""
        entry = MemoryEntry(
            id=memory_id,
            content=content,
            metadata=metadata or {},
        )
        self._memories[memory_id] = entry
        return entry

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[MemoryEntry]:
        """Search for similar memories (simplified text matching for dev).

        In production, this performs vector similarity search via Pinecone.
        """
        results: list[MemoryEntry] = []

        query_lower = query.lower()
        for memory in self._memories.values():
            # Simple text matching for development
            if query_lower in memory.content.lower():
                if filter_metadata:
                    if all(memory.metadata.get(k) == v for k, v in filter_metadata.items()):
                        results.append(memory)
                else:
                    results.append(memory)

        return results[:top_k]

    async def get_user_preferences(self, user_id: str) -> list[MemoryEntry]:
        """Retrieve stored preferences for a specific user."""
        return await self.search(
            query="preference",
            filter_metadata={"user_id": user_id, "type": "preference"},
        )

    async def store_interaction(
        self,
        session_id: str,
        user_id: str,
        summary: str,
        intent: str,
    ) -> MemoryEntry:
        """Store a summarized interaction for future RAG retrieval."""
        return await self.store(
            memory_id=f"interaction-{session_id}",
            content=summary,
            metadata={
                "user_id": user_id,
                "session_id": session_id,
                "type": "interaction",
                "intent": intent,
            },
        )

    async def store_user_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: str,
    ) -> MemoryEntry:
        """Store a user preference (e.g., 'always prefers refrigerated trucks')."""
        return await self.store(
            memory_id=f"pref-{user_id}-{preference_key}",
            content=f"User preference: {preference_key} = {preference_value}",
            metadata={
                "user_id": user_id,
                "type": "preference",
                "key": preference_key,
                "value": preference_value,
            },
        )


# Global memory instance
vector_memory = VectorMemory()
