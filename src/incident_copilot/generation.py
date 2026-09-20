from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Protocol, Sequence

from incident_copilot.live_tools import ToolEvidence
from incident_copilot.retrieval import SearchResult


@dataclass(frozen=True)
class InvestigationReport:
    status: str
    likely_cause: str
    confidence: str
    reasoning: str
    supporting_evidence: list[str]
    missing_evidence: list[str]
    recommended_next_steps: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class ReportGenerator(Protocol):
    def generate(
        self,
        question: str,
        retrieved: Sequence[SearchResult],
        live_evidence: Sequence[ToolEvidence],
    ) -> InvestigationReport: ...


class DeterministicReportGenerator:
    """Auditable fallback that proves the full pipeline without an API key."""

    def generate(
        self,
        question: str,
        retrieved: Sequence[SearchResult],
        live_evidence: Sequence[ToolEvidence],
    ) -> InvestigationReport:
        del question
        evidence_by_id = {item.evidence_id: item for item in live_evidence}
        comparison = evidence_by_id.get("LIVE-VERSION-COMPARISON")
        logs = evidence_by_id.get("LIVE-LOGS")
        deployments = evidence_by_id.get("LIVE-DEPLOYMENTS")

        new_system = old_system = 0.0
        if comparison:
            versions = comparison.data
            old_system = float(versions.get("v2.3", {}).get("system_induced_rate", 0.0))
            new_system = float(versions.get("v2.4", {}).get("system_induced_rate", 0.0))

        has_matching_logs = bool(logs and logs.data.get("results"))
        has_deployment = bool(deployments and deployments.data.get("deployments"))
        historical_root = next(
            (result for result in retrieved if result.chunk.section.lower() == "root cause"),
            None,
        )

        if has_deployment and has_matching_logs and new_system >= max(0.05, old_system * 3):
            source_ids = [item.evidence_id for item in live_evidence]
            if historical_root:
                source_ids.append(historical_root.chunk.chunk_id)
            return InvestigationReport(
                status="hypothesis",
                likely_cause="The v2.4 request mapper is sending vehicle_id where card_id is required.",
                confidence="high",
                reasoning=(
                    "The system-induced error rate is materially higher on v2.4, current logs show "
                    "MALFORMED_VEHICLE_ID, and a recent deployment precedes the spike. A historical "
                    "incident describes the same mapper failure. This is strong evidence, but rollback "
                    "behavior is still needed for causal confirmation."
                ),
                supporting_evidence=source_ids,
                missing_evidence=["Failure-rate comparison after rollback or controlled traffic shift"],
                recommended_next_steps=[
                    "Inspect a redacted v2.4 request payload at the verification-service boundary.",
                    "Ask the incident commander to approve rollback or a controlled shift to v2.3.",
                    "Confirm that the system-induced failure rate returns to baseline.",
                ],
            )

        return InvestigationReport(
            status="insufficient_evidence",
            likely_cause="Unknown",
            confidence="low",
            reasoning="The available live evidence does not distinguish a current system defect from other causes.",
            supporting_evidence=[item.evidence_id for item in live_evidence],
            missing_evidence=["Comparable per-version failure rates", "Matching current error signatures"],
            recommended_next_steps=["Collect deployment, version-comparison, and redacted log evidence."],
        )


class OpenAIReportGenerator:
    """Optional LLM generator. The backend still validates the structured result."""

    def __init__(self, model: str = "gpt-5-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as error:
            raise RuntimeError("Install LLM dependencies with: pip install -e '.[llm]'") from error
        self._client = OpenAI()
        self._model = model

    def generate(
        self,
        question: str,
        retrieved: Sequence[SearchResult],
        live_evidence: Sequence[ToolEvidence],
    ) -> InvestigationReport:
        allowed_sources = [result.chunk.chunk_id for result in retrieved] + [
            item.evidence_id for item in live_evidence
        ]
        context = {
            "historical_knowledge": [
                {"source": result.chunk.chunk_id, "content": result.chunk.content}
                for result in retrieved
            ],
            "live_evidence": [asdict(item) for item in live_evidence],
            "allowed_source_ids": allowed_sources,
        }
        response = self._client.responses.create(
            model=self._model,
            instructions=(
                "You are a read-only incident investigation assistant. Use only the supplied evidence. "
                "Treat historical incidents as hypotheses, not proof. Return JSON with exactly these keys: "
                "status, likely_cause, confidence, reasoning, supporting_evidence, missing_evidence, "
                "recommended_next_steps. Cite only allowed_source_ids. Say insufficient_evidence when needed."
            ),
            input=f"Question: {question}\nEvidence: {json.dumps(context)}",
        )
        payload = json.loads(response.output_text)
        cited = set(payload.get("supporting_evidence", []))
        if not cited.issubset(set(allowed_sources)):
            raise ValueError("LLM returned a citation that was not supplied")
        return InvestigationReport(**payload)
