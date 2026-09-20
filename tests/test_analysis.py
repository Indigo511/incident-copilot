from datetime import datetime, timezone
from pathlib import Path
import unittest

from incident_copilot.analysis import ErrorCategory, UnlockRequestLog, compare_versions
from incident_copilot.chunking import chunk_markdown


class TestUnlockRequestLog(unittest.TestCase):
    def test_backend_maps_known_error_code_to_system_category(self) -> None:
        log = UnlockRequestLog(
            datetime.now(timezone.utc), "req-1", "v2.4", 500, "MALFORMED_VEHICLE_ID"
        )
        self.assertEqual(log.error_category, ErrorCategory.SYSTEM_INDUCED)

    def test_version_comparison_keeps_user_and_system_failures_separate(self) -> None:
        now = datetime.now(timezone.utc)
        logs = [
            UnlockRequestLog(now, "1", "v2.3", 200, None),
            UnlockRequestLog(now, "2", "v2.3", 400, "INVALID_VEHICLE_NUMBER"),
            UnlockRequestLog(now, "3", "v2.4", 500, "MALFORMED_VEHICLE_ID"),
            UnlockRequestLog(now, "4", "v2.4", 500, "MALFORMED_VEHICLE_ID"),
        ]
        results = {result.version: result for result in compare_versions(logs)}
        self.assertEqual(results["v2.3"].user_induced_error_rate, 0.5)
        self.assertEqual(results["v2.3"].system_induced_error_rate, 0.0)
        self.assertEqual(results["v2.4"].user_induced_error_rate, 0.0)
        self.assertEqual(results["v2.4"].system_induced_error_rate, 1.0)

    def test_chunking_keeps_document_title_and_section_context(self) -> None:
        path = "knowledge/incidents/INC-104-card-unlock-v2-4.md"
        chunks = chunk_markdown(Path(path))
        root_cause = next(chunk for chunk in chunks if chunk.section == "Root cause")
        self.assertIn("INC-104: Card unlock failures after v2.4", root_cause.content)
        self.assertIn("Section: Root cause", root_cause.content)
        self.assertIn("vehicle_id", root_cause.content)


if __name__ == "__main__":
    unittest.main()
