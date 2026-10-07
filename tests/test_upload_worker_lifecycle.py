import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from backend.api import routes
from backend.config import UPLOADS_DIR
from backend.database.repository import SongRepository
from backend.models.schemas import (
    AnalysisStatusEnum,
    AnalysisStatusResponse,
    AudioMetadata,
    BeatGrid,
    KeyAnalysis,
    MeterAnalysis,
    PipelineMetadata,
    SongAnalysis,
    TempoAnalysis,
)


def make_analysis(song_id: str) -> SongAnalysis:
    return SongAnalysis(
        id=song_id,
        title="Lifecycle test",
        metadata=AudioMetadata(
            filename="lifecycle.wav",
            duration=3.0,
            sample_rate=44100,
            channels=2,
            format="wav",
            file_size_bytes=0,
            file_hash="test-hash",
        ),
        pipeline_metadata=PipelineMetadata(),
        key=KeyAnalysis(tonic="C", mode="major", display="C Major", confidence=1.0),
        tempo=TempoAnalysis(bpm=120.0, confidence=1.0),
        meter=MeterAnalysis(),
        beat_grid=BeatGrid(bpm=120.0, beats=[0.0, 0.5], downbeats=[0.0]),
        sections=[],
        chords=[],
    )


class TestUploadWorkerLifecycle(unittest.TestCase):
    def _queued_task(self, analysis_id: str) -> None:
        routes.ACTIVE_TASKS[analysis_id] = AnalysisStatusResponse(
            analysis_id=analysis_id,
            status=AnalysisStatusEnum.QUEUED,
            current_stage="QUEUED",
            message="queued",
        )

    def test_success_ingests_and_removes_temporary_upload(self):
        analysis_id = f"lifecycle-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(dir=UPLOADS_DIR) as tmpdir:
            source = Path(tmpdir) / "upload.wav"
            source.write_bytes(b"not decoded by the mocked pipeline")
            self._queued_task(analysis_id)
            analysis = make_analysis(analysis_id)
            try:
                with patch.object(routes.PIPELINE, "process", return_value=analysis):
                    routes.run_pipeline_worker(analysis_id, source, analysis.title)

                self.assertEqual(routes.ACTIVE_TASKS[analysis_id].status, AnalysisStatusEnum.COMPLETED)
                self.assertFalse(source.exists())
                song = SongRepository.get_song(analysis_id)
                self.assertIsNotNone(song)
                self.assertTrue(Path(song["audio_path"]).is_file())
            finally:
                SongRepository.delete_song(analysis_id)
                routes.ACTIVE_TASKS.pop(analysis_id, None)
                routes.ANALYSIS_RESULTS.pop(analysis_id, None)
                routes.AUDIO_FILE_PATHS.pop(analysis_id, None)

    def test_analysis_failure_removes_temporary_upload(self):
        analysis_id = f"failure-{uuid.uuid4().hex[:8]}"
        with tempfile.TemporaryDirectory(dir=UPLOADS_DIR) as tmpdir:
            source = Path(tmpdir) / "upload.wav"
            source.write_bytes(b"analysis failure fixture")
            self._queued_task(analysis_id)
            with patch.object(routes.PIPELINE, "process", side_effect=RuntimeError("expected failure")):
                routes.run_pipeline_worker(analysis_id, source, "Failure test")

            self.assertEqual(routes.ACTIVE_TASKS[analysis_id].status, AnalysisStatusEnum.FAILED)
            self.assertFalse(source.exists())
            routes.ACTIVE_TASKS.pop(analysis_id, None)


if __name__ == "__main__":
    unittest.main()
