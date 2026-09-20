import importlib.util
import unittest


@unittest.skipUnless(importlib.util.find_spec("fastapi") and importlib.util.find_spec("httpx"),
                     "Install the test-api extra to run HTTP integration tests")
class ApiTests(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from incident_copilot.api import app
        self.client = TestClient(app)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

    def test_investigation_discloses_synthetic_data(self):
        response = self.client.post("/v1/investigations", json={"question": "Check card unlock health today"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data_mode"], "synthetic_fixture")
        self.assertEqual(response.json()["report"]["status"], "hypothesis")

    def test_bad_requests(self):
        for body in ({"question": "     "}, {"question": "Check health", "service": "payments"}, {}):
            with self.subTest(body=body):
                self.assertEqual(self.client.post("/v1/investigations", json=body).status_code, 422)
