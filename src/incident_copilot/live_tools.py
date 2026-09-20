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
        if fixture_path.is_dir():
            self._scenarios = {
                path.stem: json.loads(path.read_text(encoding="utf-8"))
                for path in sorted(fixture_path.glob("*.json"))
            }
            self.default_scenario = "deployment_regression"
        else:
            self._scenarios = {
                fixture_path.stem: json.loads(fixture_path.read_text(encoding="utf-8"))
            }
            self.default_scenario = fixture_path.stem
        if not self._scenarios:
            raise ValueError("at least one fixture scenario is required")
        if self.default_scenario not in self._scenarios:
            self.default_scenario = next(iter(self._scenarios))
        for scenario_name, data in self._scenarios.items():
            self._validate_scenario(scenario_name, data)

    @staticmethod
    def _validate_scenario(name: str, data: dict[str, Any]) -> None:
        required = {"context", "deployments", "version_comparison", "log_summary", "dependency_health"}
        missing = required - set(data)
        if missing:
            raise ValueError(f"Scenario '{name}' is missing fields: {', '.join(sorted(missing))}")
        context = data["context"]
        required_context = {"scenario_id", "service", "current_version", "baseline_version", "time_range"}
        if not isinstance(context, dict) or required_context - set(context):
            raise ValueError(f"Scenario '{name}' has incomplete context")
        if context["scenario_id"] != name:
            raise ValueError(f"Scenario id '{context['scenario_id']}' does not match filename '{name}'")
        service = context["service"]
        cohorts = data["version_comparison"].get(service, {})
        if context["current_version"] not in cohorts or context["baseline_version"] not in cohorts:
            raise ValueError(f"Scenario '{name}' is missing its current or baseline cohort")

    @property
    def available_scenarios(self) -> tuple[str, ...]:
        return tuple(self._scenarios)

    def _data(self, scenario: str | None) -> dict[str, Any]:
        selected = scenario or self.default_scenario
        try:
            return self._scenarios[selected]
        except KeyError as error:
            choices = ", ".join(self.available_scenarios)
            raise ValueError(f"Unknown scenario '{selected}'. Choose one of: {choices}") from error

    def get_investigation_context(self, service: str, scenario: str | None = None) -> ToolEvidence:
        context = self._data(scenario).get("context", {})
        service_context = context if context.get("service") == service else {}
        summary = (
            f"Scenario={service_context.get('scenario_id')}; current={service_context.get('current_version')}; "
            f"baseline={service_context.get('baseline_version')}; window={service_context.get('time_range')}"
            if service_context else "No investigation context available."
        )
        return ToolEvidence("LIVE-CONTEXT", "get_investigation_context", summary, service_context)

    def get_recent_deployments(self, service: str, scenario: str | None = None) -> ToolEvidence:
        deployments = [
            item for item in self._data(scenario).get("deployments", []) if item["service"] == service
        ]
        summary = "No recent deployment found."
        if deployments:
            latest = deployments[-1]
            summary = (
                f"{latest['version']} was deployed at {latest['deployed_at']} "
                f"to {latest['region']}."
            )
        return ToolEvidence("LIVE-DEPLOYMENTS", "get_recent_deployments", summary, {"deployments": deployments})

    def compare_versions(self, service: str, scenario: str | None = None) -> ToolEvidence:
        comparison = self._data(scenario).get("version_comparison", {}).get(service, {})
        summary = "; ".join(
            f"{version}: system={rates['system_induced_rate']:.1%}, "
            f"user={rates['user_induced_rate']:.1%}"
            for version, rates in comparison.items()
        ) or "No version comparison available."
        return ToolEvidence("LIVE-VERSION-COMPARISON", "compare_versions", summary, comparison)

    def search_logs(self, service: str, error_code: str | None = None, scenario: str | None = None) -> ToolEvidence:
        logs = [item for item in self._data(scenario).get("log_summary", []) if item["service"] == service]
        if error_code:
            logs = [item for item in logs if item["error_code"] == error_code]
        summary = "; ".join(
            f"{item['version']} {item['error_code']}: {item['count']} events, "
            f"sample={item['safe_sample']}"
            for item in logs
        ) or "No matching logs found."
        return ToolEvidence("LIVE-LOGS", "search_logs", summary, {"results": logs})

    def get_dependency_health(self, service: str, scenario: str | None = None) -> ToolEvidence:
        dependencies = self._data(scenario).get("dependency_health", {}).get(service, [])
        summary = "; ".join(
            f"{item['dependency']}={item['status']} error_rate={item['error_rate']:.1%}"
            for item in dependencies
        ) or "No dependency-health data available."
        return ToolEvidence("LIVE-DEPENDENCIES", "get_dependency_health", summary, {"dependencies": dependencies})

    def investigate_unlock_failures(self, service: str, scenario: str | None = None) -> list[ToolEvidence]:
        return [
            self.get_investigation_context(service, scenario),
            self.get_recent_deployments(service, scenario),
            self.compare_versions(service, scenario),
            self.search_logs(service, scenario=scenario),
            self.get_dependency_health(service, scenario),
        ]
