from __future__ import annotations

from functools import lru_cache
from dataclasses import asdict
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field
except ImportError as error:  # pragma: no cover - optional adapter
    raise RuntimeError("Install API dependencies with: pip install -e '.[api]'") from error

from incident_copilot.cli import build_copilot
from incident_copilot.copilot import IncidentCopilot
from incident_copilot.feedback import SQLiteFeedbackStore


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    service: str = Field(default="card-unlock-service", min_length=1, max_length=100)
    scenario: str = Field(default="deployment_regression", min_length=1, max_length=100)


class FeedbackRequest(BaseModel):
    trace_id: str = Field(min_length=36, max_length=36)
    rating: str
    notes: str | None = Field(default=None, max_length=2000)
    actual_root_cause: str | None = Field(default=None, max_length=1000)


@lru_cache
def get_copilot() -> IncidentCopilot:
    return build_copilot()


@lru_cache
def get_feedback_store() -> SQLiteFeedbackStore:
    return SQLiteFeedbackStore(Path("/tmp/incident-copilot-feedback.db"))


app = FastAPI(title="AI Incident Investigation Copilot", version="0.4.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/investigations")
def investigate(request: InvestigationRequest) -> dict[str, object]:
    try:
        result = get_copilot().investigate(
            request.question, request.service, scenario=request.scenario
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {
        "data_mode": result.data_mode,
        "limitations": result.limitations,
        "question": result.question,
        "plan": {
            "intent": result.plan.intent,
            "time_range": {
                "start": result.plan.time_range.start,
                "end": result.plan.time_range.end,
                "source": result.plan.time_range.source,
            },
            "initial_tools": [call.name for call in result.plan.initial_tool_calls],
            "blocked_actions": result.plan.blocked_actions,
        },
        "retrieved_sources": [item.chunk.chunk_id for item in result.retrieved],
        "live_sources": [item.evidence_id for item in result.live_evidence],
        "report": result.report.to_dict(),
        "trace": result.trace.to_dict(),
    }


@app.post("/v1/feedback")
def submit_feedback(request: FeedbackRequest) -> dict[str, object]:
    copilot = get_copilot()
    if not copilot.trace_store.contains(request.trace_id):
        raise HTTPException(status_code=404, detail="Unknown investigation trace")
    try:
        feedback = get_feedback_store().record(
            request.trace_id,
            request.rating,
            request.notes,
            request.actual_root_cause,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return asdict(feedback)
