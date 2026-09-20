from pathlib import Path
import unittest

from incident_copilot.copilot import IncidentCopilot


class TestIncidentCopilot(unittest.TestCase):
    def test_e2e_investigation_returns_grounded_hypothesis(self) -> None:
        copilot = IncidentCopilot(
            Path("knowledge"), Path("data/live_incident.json")
        )
        result = copilot.investigate(
            "Why are asset-card unlocks failing after the latest release?"
        )
        self.assertEqual(result.report.status, "hypothesis")
        self.assertEqual(result.report.confidence, "high")
        self.assertIn("LIVE-LOGS", result.report.supporting_evidence)
        allowed = {item.chunk.chunk_id for item in result.retrieved} | {
            item.evidence_id for item in result.live_evidence
        }
        self.assertTrue(set(result.report.supporting_evidence).issubset(allowed))


if __name__ == "__main__":
    unittest.main()
