from pathlib import Path
import tempfile
import unittest
from uuid import uuid4

from incident_copilot.feedback import SQLiteFeedbackStore


class FeedbackTests(unittest.TestCase):
    def test_feedback_is_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteFeedbackStore(Path(directory) / "feedback.db")
            feedback = store.record(str(uuid4()), "helpful", "Useful evidence", "Mapper regression")
            self.assertEqual(feedback.rating, "helpful")
            self.assertEqual(feedback.actual_root_cause, "Mapper regression")

    def test_feedback_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteFeedbackStore(Path(directory) / "feedback.db")
            for trace_id, rating in (("bad", "helpful"), (str(uuid4()), "maybe")):
                with self.subTest(trace_id=trace_id, rating=rating), self.assertRaises(ValueError):
                    store.record(trace_id, rating)


if __name__ == "__main__":
    unittest.main()
