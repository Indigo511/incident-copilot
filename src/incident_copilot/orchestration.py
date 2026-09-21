from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Sequence

from incident_copilot.live_tools import FixtureIncidentTools, ToolEvidence


@dataclass(frozen=True)
class ResolvedTimeRange:
    start: str
    end: str
    source: str


@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]
    reason: str


@dataclass(frozen=True)
class InvestigationPlan:
    intent: str
    time_range: ResolvedTimeRange
    initial_tool_calls: tuple[ToolCall, ...]
    blocked_actions: tuple[str, ...]


@dataclass(frozen=True)
class ToolExecution:
    name: str
    arguments: dict[str, Any]
    evidence_id: str
    reason: str
    latency_ms: float


@dataclass(frozen=True)
class InvestigationTrace:
    trace_id: str
    question: str
    intent: str
    time_range: ResolvedTimeRange
    retrieved_sources: tuple[str, ...]
    tool_executions: tuple[ToolExecution, ...]
    blocked_actions: tuple[str, ...]
    report_status: str
    generator: str
    estimated_input_characters: int
    total_latency_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TimeRangeResolver:
    _LAST_MINUTES = re.compile(r"\blast\s+(\d{1,4})\s+minutes?\b", re.IGNORECASE)
    _LAST_HOURS = re.compile(r"\blast\s+(\d{1,3})\s+hours?\b", re.IGNORECASE)

    def resolve(self, question: str, now: datetime | None = None) -> ResolvedTimeRange:
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        current = current.astimezone(timezone.utc)

        minute_match = self._LAST_MINUTES.search(question)
        if minute_match:
            minutes = min(int(minute_match.group(1)), 24 * 60)
            return self._range(current - timedelta(minutes=minutes), current, "last_minutes")

        hour_match = self._LAST_HOURS.search(question)
        if hour_match:
            hours = min(int(hour_match.group(1)), 7 * 24)
            return self._range(current - timedelta(hours=hours), current, "last_hours")

        if "today" in question.lower():
            start = current.replace(hour=0, minute=0, second=0, microsecond=0)
            return self._range(start, current, "today_utc")

        return self._range(current - timedelta(hours=1), current, "default_last_hour")

    @staticmethod
    def _range(start: datetime, end: datetime, source: str) -> ResolvedTimeRange:
        return ResolvedTimeRange(start.isoformat(), end.isoformat(), source)


class RuleBasedAgentPlanner:
    """Testable planner; designed to be replaceable by an LLM tool-call planner."""

    _MUTATING_TERMS = {
        "restart": "restart service",
        "rollback": "rollback deployment",
        "roll back": "rollback deployment",
        "shift traffic": "shift traffic",
        "scale up": "scale service",
        "disable feature": "disable feature",
    }

    def __init__(self, time_ranges: TimeRangeResolver | None = None) -> None:
        self.time_ranges = time_ranges or TimeRangeResolver()

    def plan(
        self,
        question: str,
        service: str,
        scenario: str,
        now: datetime | None = None,
    ) -> InvestigationPlan:
        query = question.lower()
        resolved = self.time_ranges.resolve(question, now)
        historical_only = any(term in query for term in ("seen before", "similar incident", "historical"))
        health = any(term in query for term in ("health", "healthy", "status"))
        diagnosis = any(term in query for term in ("why", "cause", "failure", "failing", "error", "latency", "timeout"))
        deployment = any(term in query for term in ("deploy", "release", "version", "rollout"))
        log_request = any(term in query for term in ("log", "exception", "error code"))
        dependency = any(term in query for term in ("dependency", "downstream", "timeout", "latency"))

        if historical_only and not (health or diagnosis or deployment):
            intent = "historical_similarity"
        elif health:
            intent = "health_check"
        elif deployment:
            intent = "deployment_investigation"
        else:
            intent = "incident_diagnosis"

        shared = {"service": service, "scenario": scenario, "start": resolved.start, "end": resolved.end}
        calls = [ToolCall("get_investigation_context", shared, "Establish comparable versions and fixture window")]
        if not historical_only or health or diagnosis or deployment:
            calls.append(ToolCall("get_metrics", shared, "Measure current and baseline failure rates"))
        if deployment:
            calls.append(ToolCall("get_recent_deployments", shared, "Correlate changes with the incident window"))
        if health or dependency:
            calls.append(ToolCall("get_service_dependencies", shared, "Check whether dependencies are healthy"))
        if log_request:
            calls.append(ToolCall("search_logs", shared, "Inspect requested error signatures"))

        blocked = tuple(
            action for term, action in self._MUTATING_TERMS.items() if term in query
        )
        return InvestigationPlan(intent, resolved, tuple(calls), blocked)


class ReadOnlyToolExecutor:
    """Allowlisted fixture executor with bounded adaptive investigation."""

    MAX_TOOL_CALLS = 6

    def __init__(self, tools: FixtureIncidentTools) -> None:
        self.tools = tools
        self._handlers: dict[str, Callable[[str, str], ToolEvidence]] = {
            "get_investigation_context": tools.get_investigation_context,
            "get_metrics": tools.compare_versions,
            "get_recent_deployments": tools.get_recent_deployments,
            "search_logs": lambda service, scenario: tools.search_logs(service, scenario=scenario),
            "get_service_dependencies": tools.get_dependency_health,
        }

    @property
    def allowed_tools(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    def execute(self, plan: InvestigationPlan, service: str, scenario: str) -> tuple[list[ToolEvidence], list[ToolExecution]]:
        evidence: list[ToolEvidence] = []
        records: list[ToolExecution] = []
        pending = list(plan.initial_tool_calls)
        executed: set[str] = set()

        while pending and len(records) < self.MAX_TOOL_CALLS:
            call = pending.pop(0)
            if call.name in executed:
                continue
            if call.name not in self._handlers:
                raise ValueError(f"Tool '{call.name}' is not in the read-only allowlist")
            if call.arguments.get("service") != service or call.arguments.get("scenario") != scenario:
                raise ValueError("tool arguments do not match the investigation scope")

            started = time.perf_counter()
            result = self._handlers[call.name](service, scenario)
            elapsed = (time.perf_counter() - started) * 1000
            evidence.append(result)
            records.append(ToolExecution(call.name, call.arguments, result.evidence_id, call.reason, elapsed))
            executed.add(call.name)

            if call.name == "get_metrics" and self._has_failure_spike(evidence):
                pending.extend(
                    self._missing_calls(
                        executed | {item.name for item in pending},
                        call.arguments,
                        [
                            ("search_logs", "Inspect signatures after metrics showed an anomaly"),
                            ("get_recent_deployments", "Check whether a recent change aligns with the anomaly"),
                        ],
                    )
                )
            if call.name == "search_logs" and self._has_timeout(evidence):
                pending.extend(
                    self._missing_calls(
                        executed | {item.name for item in pending},
                        call.arguments,
                        [("get_service_dependencies", "Timeout logs require downstream health evidence")],
                    )
                )

        return evidence, records

    @staticmethod
    def _missing_calls(
        existing: set[str], arguments: dict[str, Any], requested: Sequence[tuple[str, str]]
    ) -> list[ToolCall]:
        return [ToolCall(name, arguments, reason) for name, reason in requested if name not in existing]

    @staticmethod
    def _has_failure_spike(evidence: Sequence[ToolEvidence]) -> bool:
        context = next((item.data for item in evidence if item.evidence_id == "LIVE-CONTEXT"), {})
        metrics = next((item.data for item in evidence if item.evidence_id == "LIVE-VERSION-COMPARISON"), {})
        current = metrics.get(context.get("current_version"), {})
        return sum(float(current.get(key, 0)) for key in ("system_induced_rate", "user_induced_rate")) >= 0.05

    @staticmethod
    def _has_timeout(evidence: Sequence[ToolEvidence]) -> bool:
        logs = next((item.data.get("results", []) for item in evidence if item.evidence_id == "LIVE-LOGS"), [])
        return any("TIMEOUT" in str(item.get("error_code", "")) for item in logs)
