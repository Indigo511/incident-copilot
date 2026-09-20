from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToolEvidence:
    evidence_id: str
    tool: str
    summary: str
    data: dict[str, Any]


class FixtureIncidentTools:
    """Read-only stand-in for Datadog/Splunk/deployment APIs."""

    def __init__(self, fixture_path: Path) -> None:
        self._data = json.loads(fixture_path.read_text(encoding="utf-8"))

    def get_recent_deployments(self, service: str) -> ToolEvidence:
        deployments = [
            item for item in self._data["deployments"] if item["service"] == service
        ]
        summary = "No recent deployment found."
        if deployments:
            latest = deployments[-1]
            summary = (
                f"{latest['version']} was deployed at {latest['deployed_at']} "
                f"to {latest['region']}."
            )
        return ToolEvidence("LIVE-DEPLOYMENTS", "get_recent_deployments", summary, {"deployments": deployments})

    def compare_versions(self, service: str) -> ToolEvidence:
        comparison = self._data["version_comparison"].get(service, {})
        summary = "; ".join(
            f"{version}: system={rates['system_induced_rate']:.1%}, "
            f"user={rates['user_induced_rate']:.1%}"
            for version, rates in comparison.items()
        ) or "No version comparison available."
        return ToolEvidence("LIVE-VERSION-COMPARISON", "compare_versions", summary, comparison)

    def search_logs(self, service: str, error_code: str | None = None) -> ToolEvidence:
        logs = [item for item in self._data["log_summary"] if item["service"] == service]
        if error_code:
            logs = [item for item in logs if item["error_code"] == error_code]
        summary = "; ".join(
            f"{item['version']} {item['error_code']}: {item['count']} events, "
            f"sample={item['safe_sample']}"
            for item in logs
        ) or "No matching logs found."
        return ToolEvidence("LIVE-LOGS", "search_logs", summary, {"results": logs})

    def investigate_unlock_failures(self, service: str) -> list[ToolEvidence]:
        return [
            self.get_recent_deployments(service),
            self.compare_versions(service),
            self.search_logs(service, "MALFORMED_VEHICLE_ID"),
        ]
