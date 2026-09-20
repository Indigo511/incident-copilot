from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from incident_copilot.chunking import chunk_directory
from incident_copilot.embeddings import EmbeddingProvider, HashingEmbeddingProvider
from incident_copilot.generation import DeterministicReportGenerator, InvestigationReport, ReportGenerator
from incident_copilot.live_tools import FixtureIncidentTools, ToolEvidence
from incident_copilot.retrieval import InMemoryHybridRetriever, SearchResult


@dataclass(frozen=True)
class Investigation:
    question: str
    retrieved: list[SearchResult]
    live_evidence: list[ToolEvidence]
    report: InvestigationReport


class IncidentCopilot:
    def __init__(
        self,
        knowledge_directory: Path,
        fixture_path: Path,
        embedding_provider: EmbeddingProvider | None = None,
        report_generator: ReportGenerator | None = None,
    ) -> None:
        chunks = chunk_directory(knowledge_directory)
        self.retriever = InMemoryHybridRetriever(
            chunks, embedding_provider or HashingEmbeddingProvider()
        )
        self.tools = FixtureIncidentTools(fixture_path)
        self.report_generator = report_generator or DeterministicReportGenerator()

    def investigate(
        self,
        question: str,
        service: str = "card-unlock-service",
        retrieval_limit: int = 5,
    ) -> Investigation:
        retrieved = self.retriever.search(question, limit=retrieval_limit)
        live_evidence = self.tools.investigate_unlock_failures(service)
        report = self.report_generator.generate(question, retrieved, live_evidence)
        return Investigation(question, retrieved, live_evidence, report)
