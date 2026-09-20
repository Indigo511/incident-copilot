from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from incident_copilot.chunking import KnowledgeChunk
from incident_copilot.embeddings import EmbeddingProvider, cosine_similarity, tokenize


@dataclass(frozen=True)
class SearchResult:
    chunk: KnowledgeChunk
    semantic_score: float
    keyword_score: float
    section_score: float
    final_score: float


class InMemoryHybridRetriever:
    """Hybrid semantic and exact-token retrieval for the runnable first version."""

    def __init__(
        self,
        chunks: Iterable[KnowledgeChunk],
        embedding_provider: EmbeddingProvider,
        semantic_weight: float = 0.7,
    ) -> None:
        self.chunks = list(chunks)
        if not self.chunks:
            raise ValueError("at least one knowledge chunk is required")
        if not 0.0 <= semantic_weight <= 1.0:
            raise ValueError("semantic_weight must be between 0 and 1")
        self.embedding_provider = embedding_provider
        self.semantic_weight = semantic_weight
        self._vectors = embedding_provider.embed([chunk.content for chunk in self.chunks])

    def search(
        self,
        query: str,
        limit: int = 5,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        if limit <= 0:
            return []
        query_vector = self.embedding_provider.embed([query])[0]
        query_tokens = set(tokenize(query))
        query_lower = query.lower()
        results: list[SearchResult] = []

        for chunk, vector in zip(self.chunks, self._vectors):
            if document_id and chunk.document_id != document_id:
                continue
            semantic = max(0.0, cosine_similarity(query_vector, vector))
            chunk_tokens = set(tokenize(chunk.content))
            keyword = len(query_tokens & chunk_tokens) / len(query_tokens) if query_tokens else 0.0
            section_score = self._section_intent_score(query_lower, chunk.section)
            final = (
                self.semantic_weight * semantic
                + (1.0 - self.semantic_weight) * keyword
                + section_score
            )
            results.append(SearchResult(chunk, semantic, keyword, section_score, final))

        return sorted(results, key=lambda result: result.final_score, reverse=True)[:limit]

    @staticmethod
    def _section_intent_score(query: str, section: str) -> float:
        normalized_section = section.lower()
        if any(term in query for term in ("user", "customer mistake", "entered incorrectly")) and "user-induced" in normalized_section:
            return 0.12
        if any(term in query for term in ("why", "cause", "caused")) and "root cause" in normalized_section and "user" not in query:
            return 0.12
        if any(term in query for term in ("fix", "resolve", "recover")) and "resolution" in normalized_section:
            return 0.12
        if any(term in query for term in ("prevent", "avoid recurrence")) and "prevention" in normalized_section:
            return 0.12
        return 0.0
