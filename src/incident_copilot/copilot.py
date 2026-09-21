from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from uuid import uuid4

from incident_copilot.chunking import chunk_directory
from incident_copilot.embeddings import EmbeddingProvider, HashingEmbeddingProvider
from incident_copilot.generation import DeterministicReportGenerator, InvestigationReport, ReportGenerator, validate_report
from incident_copilot.feedback import InMemoryTraceStore
from incident_copilot.live_tools import FixtureIncidentTools, ToolEvidence
from incident_copilot.orchestration import (
    InvestigationPlan,
    InvestigationTrace,
    ReadOnlyToolExecutor,
    RuleBasedAgentPlanner,
)
from incident_copilot.retrieval import InMemoryHybridRetriever, SearchResult


@dataclass(frozen=True)
class Investigation:
    question: str
    retrieved: list[SearchResult]
    live_evidence: list[ToolEvidence]
    report: InvestigationReport
    plan: InvestigationPlan
    trace: InvestigationTrace
    data_mode: str = "synthetic_fixture"
    limitations: tuple[str, ...] = (
        "Not live production data; resolved time ranges are recorded but fixtures are static.",
        "The current tool planner is deterministic; it is replaceable by an LLM planner.",
        "Citation membership is validated; claim-level faithfulness is not guaranteed.",
    )


class IncidentCopilot:
    def __init__(
        self,
        knowledge_directory: Path,
        fixture_path: Path,
        embedding_provider: EmbeddingProvider | None = None,
        report_generator: ReportGenerator | None = None,
        trace_store: InMemoryTraceStore | None = None,
    ) -> None:
        chunks = chunk_directory(knowledge_directory)
        self.retriever = InMemoryHybridRetriever(
            chunks, embedding_provider or HashingEmbeddingProvider()
        )
        self.tools = FixtureIncidentTools(fixture_path)
        self.planner = RuleBasedAgentPlanner()
        self.tool_executor = ReadOnlyToolExecutor(self.tools)
        self.report_generator = report_generator or DeterministicReportGenerator()
        self.trace_store = trace_store or InMemoryTraceStore()

    def investigate(
        self,
        question: str,
        service: str = "card-unlock-service",
        retrieval_limit: int = 5,
        scenario: str | None = None,
    ) -> Investigation:
        if not isinstance(question, str) or not 5 <= len(question.strip()) <= 1000:
            raise ValueError("question must contain between 5 and 1000 non-padding characters")
        if service != "card-unlock-service":
            raise ValueError("Only card-unlock-service is supported by this fixture")
        if type(retrieval_limit) is not int or not 1 <= retrieval_limit <= 20:
            raise ValueError("retrieval_limit must be between 1 and 20")
        question = question.strip()
        started = time.perf_counter()
        retrieved = self.retriever.search(question, limit=retrieval_limit)
        selected_scenario = scenario or self.tools.default_scenario
        plan = self.planner.plan(question, service, selected_scenario)
        live_evidence, tool_executions = self.tool_executor.execute(
            plan, service, selected_scenario
        )
        report = self.report_generator.generate(question, retrieved, live_evidence)
        validate_report(report, {item.chunk.chunk_id for item in retrieved} |
                        {item.evidence_id for item in live_evidence})
        trace = InvestigationTrace(
            trace_id=str(uuid4()),
            question=question,
            intent=plan.intent,
            time_range=plan.time_range,
            retrieved_sources=tuple(item.chunk.chunk_id for item in retrieved),
            tool_executions=tuple(tool_executions),
            blocked_actions=plan.blocked_actions,
            report_status=report.status,
            generator=type(self.report_generator).__name__,
            estimated_input_characters=(
                len(question)
                + sum(len(item.chunk.content) for item in retrieved)
                + sum(len(item.summary) for item in live_evidence)
            ),
            total_latency_ms=(time.perf_counter() - started) * 1000,
        )
        self.trace_store.record(trace)
        return Investigation(
            question,
            retrieved,
            live_evidence,
            report,
            plan,
            trace,
            data_mode=f"synthetic_fixture:{selected_scenario}",
        )
