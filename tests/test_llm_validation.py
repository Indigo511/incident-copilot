import json
from types import SimpleNamespace
from unittest.mock import Mock
import unittest

from incident_copilot.generation import OpenAIReportGenerator


class LlmValidationTests(unittest.TestCase):
    def generator(self, payload):
        generator = OpenAIReportGenerator.__new__(OpenAIReportGenerator)
        generator._model = "mock-model"
        generator._client = Mock()
        generator._client.responses.create.return_value = SimpleNamespace(output_text=json.dumps(payload))
        return generator

    def payload(self):
        return {"status": "insufficient_evidence", "confidence": "low", "likely_cause": "Unknown",
                "reasoning": "No evidence", "supporting_evidence": [], "missing_evidence": ["Logs"],
                "recommended_next_steps": ["Collect logs"]}

    def test_valid_abstention(self):
        report = self.generator(self.payload()).generate("Check health", [], [])
        self.assertEqual(report.status, "insufficient_evidence")

    def test_bad_shapes_and_invented_sources(self):
        cases = [[], {}, {**self.payload(), "extra": True},
                 {**self.payload(), "supporting_evidence": ["invented"]},
                 {**self.payload(), "recommended_next_steps": "rollback"}]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                self.generator(payload).generate("Check health", [], [])
