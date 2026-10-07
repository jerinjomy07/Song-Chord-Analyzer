import unittest
import io
import time
from pathlib import Path
from starlette.testclient import TestClient

from backend.main import app
from backend.config import UPLOADS_DIR
from backend.database.repository import SongRepository
from backend.models.schemas import (
    SongAnalysis,
    AudioMetadata,
    PipelineMetadata,
    MeterAnalysis,
    TempoAnalysis,
    KeyAnalysis,
    BeatGrid,
    AnalysisStatusEnum,
    AnalysisStatusResponse
)
from backend.api.routes import ACTIVE_TASKS, MAX_PENDING_JOBS

class TestUploadLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_duplicate_upload_unlinks_temp_file(self):
        # Create a mock dummy analysis and save it in SongRepository so find_by_file_hash finds it
        mock_audio_bytes = b"LIFECYCLE_TEST_AUDIO_BYTES_12345"
        import hashlib
        audio_hash = hashlib.sha256(mock_audio_bytes).hexdigest()

        analysis = SongAnalysis(
            id="dup-test-01",
            title="Duplicate Test Song",
            metadata=AudioMetadata(
                filename="duplicate_test.wav",
                duration=30.0,
                sample_rate=44100,
                channels=2,
                format="wav",
                file_size_bytes=len(mock_audio_bytes),
                file_hash=audio_hash
            ),
            pipeline_metadata=PipelineMetadata(),
            meter=MeterAnalysis(),
            tempo=TempoAnalysis(bpm=100.0, confidence=1.0),
            key=KeyAnalysis(tonic="A", mode="major", display="A Major", confidence=1.0),
            beat_grid=BeatGrid(bpm=100.0, beats=[0.0, 1.0], downbeats=[0.0]),
            chords=[],
            sections=[]
        )

        dummy_audio_file = UPLOADS_DIR / "dummy_seed.wav"
        with open(dummy_audio_file, "wb") as f:
            f.write(mock_audio_bytes)
        try:
            SongRepository.save_analysis(analysis, dummy_audio_file, song_id="dup-test-01")
        finally:
            dummy_audio_file.unlink(missing_ok=True)

        # Count files in UPLOADS_DIR before upload
        before_uploads = list(UPLOADS_DIR.glob("*"))

        # Now upload the exact same audio bytes without force
        resp = self.client.post(
            "/analyze",
            files={"file": ("duplicate_upload.wav", io.BytesIO(mock_audio_bytes), "audio/wav")},
            data={"title": "Duplicate Try"}
        )

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "DUPLICATE_FOUND")

        # Verify that NO new file was left in UPLOADS_DIR
        after_uploads = list(UPLOADS_DIR.glob("*"))
        self.assertEqual(len(after_uploads), len(before_uploads))

    def test_queue_full_rejection(self):
        # Artificially populate ACTIVE_TASKS up to MAX_PENDING_JOBS
        dummy_task_ids = []
        for i in range(MAX_PENDING_JOBS):
            tid = f"mock-in-flight-{i}"
            dummy_task_ids.append(tid)
            ACTIVE_TASKS[tid] = AnalysisStatusResponse(
                analysis_id=tid,
                status=AnalysisStatusEnum.QUEUED,
                progress=0,
                current_stage="QUEUED",
                message="Testing queue limit"
            )

        try:
            mock_audio_bytes = b"OVERFLOW_TEST_AUDIO_BYTES_9999"
            resp = self.client.post(
                "/analyze",
                files={"file": ("overflow.wav", io.BytesIO(mock_audio_bytes), "audio/wav")},
                data={"title": "Overflow Test", "force": "true"}
            )
            self.assertEqual(resp.status_code, 429)
            self.assertIn("queue is full", resp.json()["detail"].lower())
        finally:
            for tid in dummy_task_ids:
                ACTIVE_TASKS.pop(tid, None)

if __name__ == "__main__":
    unittest.main()
