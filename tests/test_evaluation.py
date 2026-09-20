import unittest

from incident_copilot.evaluate import evaluate_recall_at_k


class TestEvaluation(unittest.TestCase):
    def test_baseline_retrieval_passes_fixture_dataset(self) -> None:
        hits, total = evaluate_recall_at_k()
        self.assertEqual(hits, total)


if __name__ == "__main__":
    unittest.main()
