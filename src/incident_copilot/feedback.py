from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

from incident_copilot.orchestration import InvestigationTrace


class InMemoryTraceStore:
    """Bounded process-local trace registry for the demo API."""

    def __init__(self, max_entries: int = 1000) -> None:
        self.max_entries = max_entries
        self._traces: dict[str, InvestigationTrace] = {}
        self._lock = Lock()

    def record(self, trace: InvestigationTrace) -> None:
        with self._lock:
            self._traces[trace.trace_id] = trace
            while len(self._traces) > self.max_entries:
                self._traces.pop(next(iter(self._traces)))

    def contains(self, trace_id: str) -> bool:
        with self._lock:
            return trace_id in self._traces


@dataclass(frozen=True)
class Feedback:
    feedback_id: str
    trace_id: str
    rating: str
    notes: str | None
    actual_root_cause: str | None
    created_at: str


class SQLiteFeedbackStore:
    """Small local store; production should use authenticated durable storage."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investigation_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    rating TEXT NOT NULL CHECK (rating IN ('helpful', 'unhelpful')),
                    notes TEXT,
                    actual_root_cause TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )

    def record(
        self,
        trace_id: str,
        rating: str,
        notes: str | None = None,
        actual_root_cause: str | None = None,
    ) -> Feedback:
        try:
            UUID(trace_id)
        except (ValueError, TypeError) as error:
            raise ValueError("trace_id must be a UUID") from error
        if rating not in {"helpful", "unhelpful"}:
            raise ValueError("rating must be helpful or unhelpful")
        for name, value, maximum in (
            ("notes", notes, 2000),
            ("actual_root_cause", actual_root_cause, 1000),
        ):
            if value is not None and (not isinstance(value, str) or len(value.strip()) > maximum):
                raise ValueError(f"{name} must be text no longer than {maximum} characters")

        feedback = Feedback(
            feedback_id=str(uuid4()),
            trace_id=trace_id,
            rating=rating,
            notes=notes.strip() if notes else None,
            actual_root_cause=actual_root_cause.strip() if actual_root_cause else None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock, self._connect() as connection:
            connection.execute(
                "INSERT INTO investigation_feedback VALUES (?, ?, ?, ?, ?, ?)",
                (
                    feedback.feedback_id,
                    feedback.trace_id,
                    feedback.rating,
                    feedback.notes,
                    feedback.actual_root_cause,
                    feedback.created_at,
                ),
            )
        return feedback
