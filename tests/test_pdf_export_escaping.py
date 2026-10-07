import tempfile
from pathlib import Path
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
from backend.export.pdf_exporter import export_to_pdf

class TestPdfExportEscaping(unittest.TestCase):
    def test_pdf_export_xml_escaping(self):
        chord_c = ChordPrediction(
            root="C",
            quality="maj",
            bass="C",
            display="C & G",
            start_time=0.0,
            end_time=2.0,
            duration=2.0,
            confidence=0.9
        )
        chord_am = ChordPrediction(
            root="A",
            quality="min",
            bass="A",
            display="Am <alt>",
            start_time=2.0,
            end_time=4.0,
            duration=2.0,
            confidence=0.9
        )

        analysis = SongAnalysis(
            id="test-esc-001",
            title="Rock & Roll <Live> & \"Unplugged\"",
            metadata=AudioMetadata(
                filename="test.wav",
                duration=120.0,
                sample_rate=44100,
                channels=2,
                format="wav",
                file_size_bytes=1000000,
                file_hash="dummyhash1234567890abcdef1234567890abcdef1234567890abcdef12345678"
            ),
            pipeline_metadata=PipelineMetadata(),
            meter=MeterAnalysis(
                numerator=4,
                denominator=4,
                display="4/4 & <special>",
                confidence=0.95
            ),
            tempo=TempoAnalysis(
                bpm=120.0,
                confidence=0.98
            ),
            key=KeyAnalysis(
                tonic="C & D",
                mode="major",
                display="C & D Major <Sharp>",
                confidence=0.90
            ),
            beat_grid=BeatGrid(bpm=120.0, beats=[0.0, 1.0, 2.0, 3.0, 4.0], downbeats=[0.0, 2.0, 4.0]),
            chords=[chord_c, chord_am],
            sections=[
                MusicalSection(
                    section_id="sec-1",
                    name="Intro & Verse <A>",
                    start_time=0.0,
                    end_time=8.0,
                    start_bar=1,
                    end_bar=2,
                    bars=[
                        Bar(
                            bar_number=1,
                            start_time=0.0,
                            end_time=2.0,
                            chords=[
                                ChordPrediction(
                                    root="C",
                                    quality="maj",
                                    bass="C",
                                    display="C & G",
                                    start_time=0.0,
                                    end_time=2.0,
                                    duration=2.0,
                                    confidence=0.9
                                )
                            ]
                        ),
                        Bar(
                            bar_number=2,
                            start_time=2.0,
                            end_time=4.0,
                            chords=[
                                ChordPrediction(
                                    root="A",
                                    quality="min",
                                    bass="A",
                                    display="Am <alt>",
                                    start_time=2.0,
                                    end_time=4.0,
                                    duration=2.0,
                                    confidence=0.9
                                )
                            ]
                        )
                    ]
                )
            ]
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "test_escaped.pdf"
            res = export_to_pdf(analysis, out_pdf)
            self.assertTrue(res.exists())
            self.assertGreater(res.stat().st_size, 0)
            with open(res, "rb") as pf:
                self.assertEqual(pf.read(4), b"%PDF")

if __name__ == "__main__":
    unittest.main()
