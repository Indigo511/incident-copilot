from __future__ import annotations

from functools import lru_cache

try:
    from fastapi import FastAPI
    from pydantic import BaseModel, Field
except ImportError as error:  # pragma: no cover - optional adapter
    raise RuntimeError("Install API dependencies with: pip install -e '.[api]'") from error

from incident_copilot.cli import build_copilot
from incident_copilot.copilot import IncidentCopilot


class InvestigationRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    service: str = Field(default="card-unlock-service", min_length=1, max_length=100)


@lru_cache
def get_copilot() -> IncidentCopilot:
    return build_copilot()


app = FastAPI(title="AI Incident Investigation Copilot", version="0.2.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/investigations")
def investigate(request: InvestigationRequest) -> dict[str, object]:
    result = get_copilot().investigate(request.question, request.service)
    return {
        "question": result.question,
        "retrieved_sources": [item.chunk.chunk_id for item in result.retrieved],
        "live_sources": [item.evidence_id for item in result.live_evidence],
        "report": result.report.to_dict(),
    }
