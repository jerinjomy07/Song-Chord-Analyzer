import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from starlette.testclient import TestClient

from backend.api import routes
from backend.main import app


class TestUploadPathSafety(unittest.TestCase):
    def test_oversized_upload_is_rejected_and_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = Path(tmpdir) / "uploads"
            upload_dir.mkdir()
            with patch.object(routes, "UPLOADS_DIR", upload_dir), patch.object(
                routes, "MAX_UPLOAD_BYTES", 8
            ):
                response = TestClient(app).post(
                    "/analyze",
                    files={"file": ("large.wav", io.BytesIO(b"0123456789"), "audio/wav")},
                    data={"title": "Oversized test", "force": "true"},
                )

            self.assertEqual(response.status_code, 413)
            self.assertEqual(list(upload_dir.iterdir()), [])

    def test_client_filename_cannot_write_outside_upload_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_dir = root / "app"
            upload_dir = app_dir / "uploads"
            upload_dir.mkdir(parents=True)
            with patch.object(routes, "UPLOADS_DIR", upload_dir), patch.object(
                routes.ANALYSIS_EXECUTOR, "submit", return_value=None
            ):
                response = TestClient(app).post(
                    "/analyze",
                    files={"file": ("../../../escape.wav", io.BytesIO(b"safe test bytes"), "audio/wav")},
                    data={"title": "Traversal test", "force": "true"},
                )

            self.assertEqual(response.status_code, 200, response.text)
            self.assertFalse((app_dir / "escape.wav").exists())
            self.assertTrue(
                all(path.resolve().is_relative_to(upload_dir.resolve()) for path in upload_dir.iterdir())
            )

    def test_invalid_and_unexpected_uploads_leave_no_temporary_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_dir = Path(tmpdir) / "uploads"
            upload_dir.mkdir()
            with patch.object(routes, "UPLOADS_DIR", upload_dir), patch.object(
                routes.ANALYSIS_EXECUTOR, "submit", return_value=None
            ):
                client = TestClient(app, raise_server_exceptions=False)
                invalid = client.post(
                    "/analyze",
                    files={"file": ("notes.txt", io.BytesIO(b"invalid"), "text/plain")},
                )
                self.assertEqual(invalid.status_code, 400)
                self.assertEqual(list(upload_dir.iterdir()), [])

                def fail_after_partial_write(source, destination):
                    destination.write_bytes(b"partial upload")
                    raise OSError("simulated write failure")

                with patch.object(routes, "save_upload_file", side_effect=fail_after_partial_write):
                    unexpected = client.post(
                        "/analyze",
                        files={"file": ("unexpected.wav", io.BytesIO(b"input"), "audio/wav")},
                    )

            self.assertEqual(unexpected.status_code, 500)
            self.assertEqual(list(upload_dir.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
