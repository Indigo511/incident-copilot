from pathlib import Path
import tempfile
import unittest

from incident_copilot.copilot import IncidentCopilot
from incident_copilot.live_tools import FixtureIncidentTools


ROOT = Path(__file__).resolve().parents[1]


class ScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.copilot = IncidentCopilot(ROOT / "knowledge", ROOT / "data/scenarios")

    def investigate(self, scenario):
        return self.copilot.investigate("Check card-unlock health after the change", scenario=scenario)

    def test_all_scenarios_are_discovered(self):
        self.assertEqual(
            set(self.copilot.tools.available_scenarios),
            {"deployment_regression", "healthy_deployment", "user_input_spike",
             "downstream_outage", "no_recent_deployment", "insufficient_sample",
             "conflicting_evidence", "multiple_deployments"},
        )

    def test_scenario_outcomes(self):
        expectations = {
            "deployment_regression": ("hypothesis", "system regression"),
            "healthy_deployment": ("healthy", "No material"),
            "user_input_spike": ("hypothesis", "user-input"),
            "downstream_outage": ("hypothesis", "Downstream degradation"),
            "no_recent_deployment": ("healthy", "No material"),
            "insufficient_sample": ("insufficient_evidence", "Unknown"),
            "conflicting_evidence": ("insufficient_evidence", "Unknown"),
            "multiple_deployments": ("insufficient_evidence", "Unknown"),
        }
        for scenario, (status, phrase) in expectations.items():
            with self.subTest(scenario=scenario):
                report = self.investigate(scenario).report
                self.assertEqual(report.status, status)
                self.assertIn(phrase, report.likely_cause)

    def test_unknown_scenario_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown scenario"):
            self.investigate("does-not-exist")

    def test_multiple_deployments_explains_ambiguity(self):
        report = self.investigate("multiple_deployments").report
        self.assertIn("Multiple recent deployments", report.reasoning)

    def test_conflicting_evidence_explains_missing_logs(self):
        report = self.investigate("conflicting_evidence").report
        self.assertIn("do not corroborate", report.reasoning)

    def test_malformed_scenario_fails_during_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text('{"context": {}}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing fields"):
                FixtureIncidentTools(path)
