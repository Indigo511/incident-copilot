from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from incident_copilot.chunking import chunk_directory
from incident_copilot.embeddings import EmbeddingProvider, HashingEmbeddingProvider
from incident_copilot.generation import DeterministicReportGenerator, InvestigationReport, ReportGenerator, validate_report
from incident_copilot.live_tools import FixtureIncidentTools, ToolEvidence
from incident_copilot.retrieval import InMemoryHybridRetriever, SearchResult


@dataclass(frozen=True)
class Investigation:
    question: str
    retrieved: list[SearchResult]
    live_evidence: list[ToolEvidence]
    report: InvestigationReport
    data_mode: str = "synthetic_fixture"
    limitations: tuple[str, ...] = (
        "Not live production data; relative dates such as 'today' are not resolved.",
        "Tool sequence is fixed, not selected by an agent.",
        "Citation membership is validated; claim-level faithfulness is not guaranteed.",
    )


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
        if not isinstance(question, str) or not 5 <= len(question.strip()) <= 1000:
            raise ValueError("question must contain between 5 and 1000 non-padding characters")
        if service != "card-unlock-service":
            raise ValueError("Only card-unlock-service is supported by this fixture")
        if type(retrieval_limit) is not int or not 1 <= retrieval_limit <= 20:
            raise ValueError("retrieval_limit must be between 1 and 20")
        question = question.strip()
        retrieved = self.retriever.search(question, limit=retrieval_limit)
        live_evidence = self.tools.investigate_unlock_failures(service)
        report = self.report_generator.generate(question, retrieved, live_evidence)
        validate_report(report, {item.chunk.chunk_id for item in retrieved} |
                        {item.evidence_id for item in live_evidence})
        return Investigation(question, retrieved, live_evidence, report)
