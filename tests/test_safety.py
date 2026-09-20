from dataclasses import replace
from pathlib import Path
import unittest

from incident_copilot.copilot import IncidentCopilot
from incident_copilot.embeddings import cosine_similarity, HashingEmbeddingProvider
from incident_copilot.generation import DeterministicReportGenerator, validate_report
from incident_copilot.live_tools import FixtureIncidentTools
from incident_copilot.retrieval import InMemoryHybridRetriever
from incident_copilot.chunking import chunk_directory

ROOT = Path(__file__).resolve().parents[1]


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.evidence = FixtureIncidentTools(ROOT / "data/scenarios").investigate_unlock_failures("card-unlock-service")
        self.generator = DeterministicReportGenerator()

    def item(self, evidence_id):
        return next(item for item in self.evidence if item.evidence_id == evidence_id)

    def report(self):
        return self.generator.generate("Check unlock health", [], self.evidence)

    def test_no_hardcoded_root_cause_without_historical_evidence(self):
        report = self.report()
        self.assertNotIn("mapper", report.likely_cause)
        self.assertNotIn("historical incident", report.reasoning.lower())
        self.assertEqual(report.confidence, "medium")

    def test_missing_baseline_does_not_become_zero_rate(self):
        self.item("LIVE-VERSION-COMPARISON").data.pop("v2.3")
        self.assertEqual(self.report().status, "insufficient_evidence")

    def test_old_version_logs_do_not_support_new_version_diagnosis(self):
        logs = self.item("LIVE-LOGS").data["results"]
        logs[:] = [item for item in logs if item["version"] == "v2.3"]
        self.assertEqual(self.report().status, "insufficient_evidence")

    def test_any_release_names_work(self):
        self.item("LIVE-CONTEXT").data["current_version"] = "release-99"
        self.item("LIVE-DEPLOYMENTS").data["deployments"][0]["version"] = "release-99"
        rates = self.item("LIVE-VERSION-COMPARISON").data
        rates["release-99"] = rates.pop("v2.4")
        for item in self.item("LIVE-LOGS").data["results"]:
            if item["version"] == "v2.4":
                item["version"] = "release-99"
        self.assertIn("release-99", self.report().likely_cause)

    def test_tiny_sample_abstains(self):
        self.item("LIVE-VERSION-COMPARISON").data["v2.4"]["request_count"] = 2
        self.assertEqual(self.report().status, "insufficient_evidence")

    def test_invalid_rates_abstain(self):
        for rate in (-0.1, 1.1, float("nan"), "0.2", True):
            with self.subTest(rate=rate):
                self.item("LIVE-VERSION-COMPARISON").data["v2.4"]["system_induced_rate"] = rate
                self.assertEqual(self.report().status, "insufficient_evidence")

    def test_citation_membership_and_shape(self):
        report = self.report()
        allowed = {item.evidence_id for item in self.evidence}
        validate_report(report, allowed)
        for changes in ({"supporting_evidence": ["invented"]},
                        {"supporting_evidence": "LIVE-LOGS"},
                        {"supporting_evidence": []},
                        {"status": "confirmed"}, {"confidence": "99%"},
                        {"reasoning": ""}, {"recommended_next_steps": [42]}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_report(replace(report, **changes), allowed)

    def test_invalid_requests(self):
        copilot = IncidentCopilot(ROOT / "knowledge", ROOT / "data/scenarios")
        for args in ({"question": "     "}, {"question": "x" * 1001},
                     {"question": "Check health", "service": "payments"},
                     {"question": "Check health", "retrieval_limit": 0}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                copilot.investigate(**args)
        self.assertEqual(copilot.investigate("Check unlock health").data_mode, "synthetic_fixture:deployment_regression")

    def test_cosine_handles_non_normalized_and_zero_vectors(self):
        self.assertAlmostEqual(cosine_similarity([3, 4], [6, 8]), 1.0)
        self.assertEqual(cosine_similarity([0, 0], [1, 2]), 0.0)
        self.assertEqual(cosine_similarity([1, 0], [-1, 0]), -1.0)
        with self.assertRaises(ValueError):
            cosine_similarity([float("nan")], [1])
        with self.assertRaises(ValueError):
            cosine_similarity([1], [1, 2])

    def test_empty_query_retrieves_nothing(self):
        retriever = InMemoryHybridRetriever(chunk_directory(ROOT / "knowledge"), HashingEmbeddingProvider())
        self.assertEqual(retriever.search("  "), [])

    def test_embedding_count_checked(self):
        class BrokenProvider:
            def embed(self, texts):
                return []
        with self.assertRaises(ValueError):
            InMemoryHybridRetriever(chunk_directory(ROOT / "knowledge"), BrokenProvider())
