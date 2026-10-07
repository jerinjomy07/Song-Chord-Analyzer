import unittest
from pathlib import Path

from starlette.testclient import TestClient

from backend.main import app


class TestApiValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_cors_allows_local_frontend_and_rejects_unknown_origin(self):
        allowed = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(allowed.headers.get("access-control-allow-credentials"), "true")

        rejected = self.client.options(
            "/api/health",
            headers={
                "Origin": "https://attacker.invalid",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertNotEqual(rejected.headers.get("access-control-allow-origin"), "https://attacker.invalid")

    def test_invalid_and_malformed_transpose_requests_return_422(self):
        for body in ({"semitones": 13}, {"semitones": -13}, {}, {"semitones": "many"}):
            response = self.client.post("/api/analysis/nonexistent/transpose", json=body)
            self.assertEqual(response.status_code, 422, (body, response.text))

    def test_malformed_youtube_info_request_returns_422(self):
        response = self.client.post("/api/sources/youtube/info", json={"not_url": "value"})
        self.assertEqual(response.status_code, 422)

    def test_missing_built_asset_returns_404(self):
        assets_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist" / "assets"
        if not assets_dir.exists():
            self.skipTest("Frontend build output is not present")
        response = self.client.get("/assets/definitely-missing-validation-asset.js")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
