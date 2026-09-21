from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from incident_copilot.cli import build_copilot
from incident_copilot.orchestration import (
    InvestigationPlan,
    ReadOnlyToolExecutor,
    ResolvedTimeRange,
    TimeRangeResolver,
    ToolCall,
)


ROOT = Path(__file__).resolve().parents[1]


class OrchestrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copilot = build_copilot()

    def test_relative_time_ranges(self):
        now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)
        resolver = TimeRangeResolver()
        thirty = resolver.resolve("failures in the last 30 minutes", now)
        self.assertEqual(thirty.start, "2026-09-21T11:30:00+00:00")
        today = resolver.resolve("health after today's deployment", now)
        self.assertEqual(today.start, "2026-09-21T00:00:00+00:00")
        self.assertEqual(today.source, "today_utc")

    def test_agent_evaluation_cases(self):
        cases = json.loads((ROOT / "evaluation/agent_cases.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(cases), 16)
        for case in cases:
            with self.subTest(question=case["question"], scenario=case["scenario"]):
                result = self.copilot.investigate(case["question"], scenario=case["scenario"])
                called = {item.name for item in result.trace.tool_executions}
                self.assertEqual(result.report.status, case["expected_status"])
                self.assertTrue(set(case["expected_tools"]).issubset(called))
                self.assertTrue(set(case.get("forbidden_tools", [])).isdisjoint(called))
                self.assertTrue(set(case.get("expected_blocked_actions", [])).issubset(result.trace.blocked_actions))
                self.assertLessEqual(len(called), ReadOnlyToolExecutor.MAX_TOOL_CALLS)

    def test_executor_rejects_unknown_and_scope_changed_tools(self):
        time_range = ResolvedTimeRange("a", "b", "test")
        for call in (
            ToolCall("restart_service", {"service": "card-unlock-service", "scenario": "deployment_regression"}, "unsafe"),
            ToolCall("get_metrics", {"service": "payments", "scenario": "deployment_regression"}, "wrong scope"),
        ):
            with self.subTest(call=call), self.assertRaises(ValueError):
                plan = InvestigationPlan("test", time_range, (call,), ())
                self.copilot.tool_executor.execute(plan, "card-unlock-service", "deployment_regression")

    def test_trace_contains_evidence_lineage(self):
        result = self.copilot.investigate(
            "Why did failures increase in the last 30 minutes?",
            scenario="deployment_regression",
        )
        self.assertEqual(result.trace.time_range.source, "last_minutes")
        self.assertEqual(result.trace.retrieved_sources, tuple(item.chunk.chunk_id for item in result.retrieved))
        self.assertTrue(all(item.latency_ms >= 0 for item in result.trace.tool_executions))


if __name__ == "__main__":
    unittest.main()
