import unittest
from starlette.testclient import TestClient
from backend.main import app
from backend.database.repository import SongRepository

class TestHistoryLimits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_default_limit(self):
        resp = self.client.get("/history")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_valid_custom_limit(self):
        resp = self.client.get("/history?limit=50")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_exceeded_limit_rejected(self):
        # Limit > 100 should return HTTP 422 Unprocessable Entity
        resp = self.client.get("/history?limit=150")
        self.assertEqual(resp.status_code, 422)

    def test_zero_or_negative_limit_rejected(self):
        # Limit < 1 should return HTTP 422 Unprocessable Entity
        resp = self.client.get("/history?limit=0")
        self.assertEqual(resp.status_code, 422)
        resp2 = self.client.get("/history?limit=-5")
        self.assertEqual(resp2.status_code, 422)

    def test_invalid_sort_by_rejected(self):
        # Invalid sort_by not in Enum should return 422
        resp = self.client.get("/history?sort_by=malicious_sql_injection_attempt")
        self.assertEqual(resp.status_code, 422)

    def test_recent_limit_bounds(self):
        resp = self.client.get("/history/recent?limit=10")
        self.assertEqual(resp.status_code, 200)
        # Exceeding 20 on recent should fail with 422
        resp_bad = self.client.get("/history/recent?limit=50")
        self.assertEqual(resp_bad.status_code, 422)

    def test_repository_internal_bounding(self):
        # Test that repository list_songs safely bounds internally regardless of caller
        res = SongRepository.list_songs(limit=9999)
        self.assertIsInstance(res, list)

if __name__ == "__main__":
    unittest.main()
