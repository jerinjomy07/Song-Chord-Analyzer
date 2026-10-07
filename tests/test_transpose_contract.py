import unittest
from backend.models.schemas import (
    SongAnalysis,
    AudioMetadata,
    PipelineMetadata,
    MeterAnalysis,
    TempoAnalysis,
    KeyAnalysis,
    BeatGrid,
    MusicalSection,
    Bar,
    ChordPrediction
)
from backend.transpose.transpose_engine import (
    normalize_transpose_semitones,
    transpose_song,
    transpose_note
)

class TestTransposeContract(unittest.TestCase):
    def test_normalize_transpose_semitones(self):
        self.assertEqual(normalize_transpose_semitones(0), 0)
        self.assertEqual(normalize_transpose_semitones(12), 0)
        self.assertEqual(normalize_transpose_semitones(-12), 0)
        self.assertEqual(normalize_transpose_semitones(24), 0)
        self.assertEqual(normalize_transpose_semitones(-24), 0)
        self.assertEqual(normalize_transpose_semitones(1), 1)
        self.assertEqual(normalize_transpose_semitones(13), 1)
        self.assertEqual(normalize_transpose_semitones(25), 1)
        self.assertEqual(normalize_transpose_semitones(-1), -1)
        self.assertEqual(normalize_transpose_semitones(-13), -1)
        self.assertEqual(normalize_transpose_semitones(11), 11)
        self.assertEqual(normalize_transpose_semitones(-11), -11)

    def test_cumulative_transpose_in_song(self):
        analysis = SongAnalysis(
            id="test-trans-001",
            title="Transposition Test",
            metadata=AudioMetadata(
                filename="test.wav",
                duration=60.0,
                sample_rate=44100,
                channels=2,
                format="wav",
                file_size_bytes=500000,
                file_hash="dummy0123456789abcdef"
            ),
            pipeline_metadata=PipelineMetadata(),
            meter=MeterAnalysis(),
            tempo=TempoAnalysis(bpm=120.0, confidence=1.0),
            key=KeyAnalysis(tonic="C", mode="major", display="C Major", confidence=1.0),
            beat_grid=BeatGrid(bpm=120.0, beats=[0.0, 1.0], downbeats=[0.0]),
            chords=[
                ChordPrediction(
                    root="C",
                    quality="maj",
                    bass="C",
                    display="C",
                    start_time=0.0,
                    end_time=1.0,
                    duration=1.0,
                    confidence=1.0
                )
            ],
            sections=[],
            transpose_semitones=0
        )

        # Transpose +7
        t1 = transpose_song(analysis, 7)
        self.assertEqual(t1.transpose_semitones, 7)
        self.assertEqual(t1.key.tonic, "G")
        self.assertEqual(t1.chords[0].root, "G")

        # Transpose another +6 (cumulative 13 -> 1)
        t2 = transpose_song(t1, 6)
        self.assertEqual(t2.transpose_semitones, 1)
        self.assertIn(t2.key.tonic, ["C#", "Db"])
        # Ensure within [-12, 12]
        self.assertGreaterEqual(t2.transpose_semitones, -12)
        self.assertLessEqual(t2.transpose_semitones, 12)

        # Reset back to 0
        t3 = transpose_song(t2, -1)
        self.assertEqual(t3.transpose_semitones, 0)
        self.assertEqual(t3.chords[0].root, "C")

if __name__ == "__main__":
    unittest.main()
