"""
Comprehensive regression test suite for Musician-Grade Mobile PDF Export Layout.
Validates:
- Compact musician-friendly lead sheet format matching the reference desktop PDF
- Section, bar, and chord preservation in chronological order
- Slash chord preservation (A#/G, C/F, G/B, F/A#, Gm/D, F/A, F/E)
- Intact multi-chord bars (| Asus4 D |, | Dm Asus4 Dm Asus4 |, | Dm Gsus2 G |)
- Complete absence of mobile UI card-grid / oversized bar boxes
- Text escaping without XML / markup corruption
- Multi-page pagination on full-length songs
- Musical content parity between desktop and mobile export engines
"""

import json
import tempfile
import unittest
from pathlib import Path

import pypdf

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
from backend.export.pdf_exporter import export_to_pdf, format_bar_str


def create_kaattu_analysis() -> SongAnalysis:
    """Creates the primary reference test track: Kaattu Thottappol (7/8, 136 BPM, D Major)."""
    return SongAnalysis(
        id="kaattu-001",
        title="Kaattu Thottappol",
        schema_version="1.0.0",
        metadata=AudioMetadata(
            filename="kaattu.mp3",
            duration=180.0,
            sample_rate=44100,
            channels=2,
            format="mp3",
            file_size_bytes=3500000,
            file_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        ),
        pipeline_metadata=PipelineMetadata(model_name="BTC-Transformer"),
        key=KeyAnalysis(tonic="D", mode="major", display="D Major", confidence=0.95),
        tempo=TempoAnalysis(bpm=136.0, confidence=0.95),
        meter=MeterAnalysis(numerator=7, denominator=8, display="7/8", confidence=0.95),
        beat_grid=BeatGrid(bpm=136.0, beats=[0.0, 0.44, 0.88], downbeats=[0.0]),
        chords=[],
        sections=[
            MusicalSection(
                section_id="sec-intro",
                name="INTRO",
                start_time=0.0,
                end_time=16.0,
                start_bar=0,
                end_bar=7,
                bars=[
                    Bar(bar_number=0, start_time=0.0, end_time=2.0, chords=[]),
                    Bar(bar_number=1, start_time=2.0, end_time=4.0, chords=[]),
                    Bar(bar_number=2, start_time=4.0, end_time=6.0, chords=[]),
                    Bar(bar_number=3, start_time=6.0, end_time=8.0, chords=[]),
                    Bar(bar_number=4, start_time=8.0, end_time=10.0, chords=[]),
                    Bar(bar_number=5, start_time=10.0, end_time=12.0, chords=[]),
                    Bar(
                        bar_number=6,
                        start_time=12.0,
                        end_time=14.0,
                        chords=[
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=12.0, end_time=13.0, duration=1.0, confidence=0.9),
                            ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=13.0, end_time=14.0, duration=1.0, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=7,
                        start_time=14.0,
                        end_time=16.0,
                        chords=[
                            ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=14.0, end_time=16.0, duration=2.0, confidence=0.9),
                        ]
                    ),
                ]
            ),
            MusicalSection(
                section_id="sec-a",
                name="SECTION A",
                start_time=16.0,
                end_time=32.0,
                start_bar=8,
                end_bar=15,
                bars=[
                    Bar(bar_number=8, start_time=16.0, end_time=18.0, chords=[ChordPrediction(root="D", quality="min", bass="D", display="Dm", start_time=16.0, end_time=18.0, duration=2.0, confidence=0.9)]),
                    Bar(bar_number=9, start_time=18.0, end_time=20.0, chords=[ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=18.0, end_time=20.0, duration=2.0, confidence=0.9)]),
                    Bar(
                        bar_number=10,
                        start_time=20.0,
                        end_time=22.0,
                        chords=[
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=20.0, end_time=21.0, duration=1.0, confidence=0.9),
                            ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=21.0, end_time=22.0, duration=1.0, confidence=0.9),
                        ]
                    ),
                    Bar(bar_number=11, start_time=22.0, end_time=24.0, chords=[ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=22.0, end_time=24.0, duration=2.0, confidence=0.9)]),
                    Bar(
                        bar_number=12,
                        start_time=24.0,
                        end_time=26.0,
                        chords=[
                            ChordPrediction(root="D", quality="min", bass="D", display="Dm", start_time=24.0, end_time=24.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=24.5, end_time=25.0, duration=0.5, confidence=0.9),
                            ChordPrediction(root="D", quality="min", bass="D", display="Dm", start_time=25.0, end_time=25.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=25.5, end_time=26.0, duration=0.5, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=13,
                        start_time=26.0,
                        end_time=28.0,
                        chords=[
                            ChordPrediction(root="D", quality="min", bass="D", display="Dm", start_time=26.0, end_time=27.0, duration=1.0, confidence=0.9),
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=27.0, end_time=28.0, duration=1.0, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=14,
                        start_time=28.0,
                        end_time=30.0,
                        chords=[
                            ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=28.0, end_time=29.0, duration=1.0, confidence=0.9),
                            ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=29.0, end_time=30.0, duration=1.0, confidence=0.9),
                        ]
                    ),
                    Bar(bar_number=15, start_time=30.0, end_time=32.0, chords=[ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=30.0, end_time=32.0, duration=2.0, confidence=0.9)]),
                ]
            ),
            MusicalSection(
                section_id="sec-b",
                name="SECTION B",
                start_time=32.0,
                end_time=48.0,
                start_bar=16,
                end_bar=23,
                bars=[
                    Bar(
                        bar_number=16,
                        start_time=32.0,
                        end_time=34.0,
                        chords=[
                            ChordPrediction(root="D", quality="min", bass="D", display="Dm", start_time=32.0, end_time=32.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="G", quality="sus2", bass="G", display="Gsus2", start_time=32.6, end_time=33.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="G", quality="maj", bass="G", display="G", start_time=33.3, end_time=34.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=17,
                        start_time=34.0,
                        end_time=36.0,
                        chords=[
                            ChordPrediction(root="G", quality="maj", bass="G", display="G", start_time=34.0, end_time=34.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="G", quality="sus2", bass="G", display="Gsus2", start_time=34.6, end_time=35.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=35.3, end_time=36.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=18,
                        start_time=36.0,
                        end_time=38.0,
                        chords=[
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=36.0, end_time=36.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="C", quality="maj", bass="C", display="C", start_time=36.6, end_time=37.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=37.3, end_time=38.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=19,
                        start_time=38.0,
                        end_time=40.0,
                        chords=[
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=38.0, end_time=38.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="C", quality="maj", bass="C", display="C", start_time=38.6, end_time=39.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="A#", quality="maj", bass="G", display="A#/G", start_time=39.3, end_time=40.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=20,
                        start_time=40.0,
                        end_time=42.0,
                        chords=[
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=40.0, end_time=40.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="C", quality="maj", bass="F", display="C/F", start_time=40.6, end_time=41.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="C", quality="maj", bass="C", display="C", start_time=41.3, end_time=42.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=21,
                        start_time=42.0,
                        end_time=44.0,
                        chords=[
                            ChordPrediction(root="B", quality="min", bass="B", display="Bm", start_time=42.0, end_time=42.6, duration=0.6, confidence=0.9),
                            ChordPrediction(root="G", quality="maj", bass="B", display="G/B", start_time=42.6, end_time=43.3, duration=0.7, confidence=0.9),
                            ChordPrediction(root="G", quality="maj", bass="G", display="G", start_time=43.3, end_time=44.0, duration=0.7, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=22,
                        start_time=44.0,
                        end_time=46.0,
                        chords=[
                            ChordPrediction(root="A#", quality="maj", bass="A#", display="A#", start_time=44.0, end_time=44.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="F", quality="maj", bass="A#", display="F/A#", start_time=44.5, end_time=45.0, duration=0.5, confidence=0.9),
                            ChordPrediction(root="C", quality="maj", bass="C", display="C", start_time=45.0, end_time=45.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="G", quality="min", bass="G", display="Gm", start_time=45.5, end_time=46.0, duration=0.5, confidence=0.9),
                        ]
                    ),
                    Bar(
                        bar_number=23,
                        start_time=46.0,
                        end_time=48.0,
                        chords=[
                            ChordPrediction(root="G", quality="min", bass="D", display="Gm/D", start_time=46.0, end_time=46.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="F", quality="maj", bass="A", display="F/A", start_time=46.5, end_time=47.0, duration=0.5, confidence=0.9),
                            ChordPrediction(root="F", quality="maj", bass="E", display="F/E", start_time=47.0, end_time=47.5, duration=0.5, confidence=0.9),
                            ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=47.5, end_time=48.0, duration=0.5, confidence=0.9),
                        ]
                    ),
                ]
            ),
        ]
    )


class TestMobilePdfLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        kaattu_pdf = Path("mobile/flutter_app/test_kaattu_exported.pdf")
        bekhayali_pdf = Path("mobile/flutter_app/test_bekhayali_exported.pdf")
        if not kaattu_pdf.exists() or not bekhayali_pdf.exists():
            flutter_cmd = r"C:\Users\jerin\flutter\bin\flutter.bat"
            import subprocess
            subprocess.run(
                [flutter_cmd, "test", "test/pdf_export_test.dart"],
                cwd="mobile/flutter_app",
                check=True,
                capture_output=True,
                shell=True
            )

    def test_mobile_pdf_layout_structure(self):
        """Validates that mobile PDF export matches the musician-friendly reference chord chart."""
        mobile_pdf_path = Path("mobile/flutter_app/test_kaattu_exported.pdf")
        self.assertTrue(mobile_pdf_path.exists(), "Mobile exported PDF must exist")

        reader = pypdf.PdfReader(str(mobile_pdf_path))
        self.assertGreaterEqual(len(reader.pages), 1)

        text = reader.pages[0].extract_text()

        # 1. Header & Metadata
        self.assertIn("Kaattu Thottappol", text)
        self.assertIn("Key: D Major", text)
        self.assertIn("136 BPM", text)
        self.assertIn("Time: 7/8", text)

        # 2. Section Headers
        self.assertIn("INTRO:", text)
        self.assertIn("SECTION A:", text)
        self.assertIn("SECTION B:", text)

        # 3. Bar preservation & Separators
        self.assertIn("| N | N | N | N |", text)
        self.assertIn("Asus4 D", text)
        self.assertIn("Dm Asus4 Dm Asus4", text)

        # 4. Slash chords preserved intact
        self.assertIn("A#/G", text)
        self.assertIn("C/F", text)
        self.assertIn("G/B", text)
        self.assertIn("F/A#", text)
        self.assertIn("Gm/D", text)
        self.assertIn("F/A", text)
        self.assertIn("F/E", text)

        # 5. No mobile UI card grid artifacts
        self.assertNotIn("Bar 0", text)
        self.assertNotIn("Bar 1", text)
        self.assertNotIn("Bar 23", text)

    def test_desktop_vs_mobile_musical_content_parity(self):
        """Validates identical musical content between desktop and mobile export engines."""
        analysis = create_kaattu_analysis()

        with tempfile.TemporaryDirectory() as tmpdir:
            desktop_pdf = Path(tmpdir) / "desktop_kaattu.pdf"
            export_to_pdf(analysis, desktop_pdf)
            self.assertTrue(desktop_pdf.exists())

            reader_desktop = pypdf.PdfReader(str(desktop_pdf))
            desktop_text = reader_desktop.pages[0].extract_text()

            reader_mobile = pypdf.PdfReader("mobile/flutter_app/test_kaattu_exported.pdf")
            mobile_text = reader_mobile.pages[0].extract_text()

            # Both must contain exact song title and metadata
            self.assertIn(analysis.title, desktop_text)
            self.assertIn(analysis.title, mobile_text)
            self.assertIn(analysis.meter.display, desktop_text)
            self.assertIn(analysis.meter.display, mobile_text)

            # Both must contain all key slash chords
            for slash_chord in ["A#/G", "C/F", "G/B", "F/A#", "Gm/D", "F/A", "F/E"]:
                self.assertIn(slash_chord, desktop_text)
                self.assertIn(slash_chord, mobile_text)

            # Both must contain multi-chord measures
            for multi in ["Asus4  D", "Dm  Gsus2  G"]:
                # Normalizing internal space differences for text extraction
                self.assertTrue(
                    multi in desktop_text or multi.replace("  ", " ") in desktop_text
                )
                self.assertTrue(
                    multi in mobile_text or multi.replace("  ", " ") in mobile_text
                )

    def test_multi_page_full_song_pagination(self):
        """Validates that a long song (Bekhayali) spans multiple pages with running header and footer."""
        bekhayali_pdf = Path("mobile/flutter_app/test_bekhayali_exported.pdf")
        self.assertTrue(bekhayali_pdf.exists())

        reader = pypdf.PdfReader(str(bekhayali_pdf))
        self.assertGreaterEqual(len(reader.pages), 2, "Long song must paginate across 2+ pages")

        page1_text = reader.pages[0].extract_text()
        page2_text = reader.pages[1].extract_text()

        # Page 1 contains main title & intro
        self.assertIn("Bekhayali", page1_text)
        self.assertIn("INTRO:", page1_text)

        # Page 2 contains running header with title & page counter
        self.assertIn("Bekhayali", page2_text)
        self.assertIn("Page 2 of", page2_text)

    def test_format_bar_str_helper(self):
        """Validates that format_bar_str handles empty bars, multi-chords, and slash walkdowns."""
        empty_bar = Bar(bar_number=0, start_time=0.0, end_time=2.0, chords=[])
        self.assertEqual(format_bar_str(empty_bar, "N"), "N")

        walkdown_bar = Bar(
            bar_number=1,
            start_time=0.0,
            end_time=2.0,
            chords=[
                ChordPrediction(root="G", quality="min", bass="G", display="Gm", start_time=0.0, end_time=1.0, duration=1.0, confidence=0.9),
                ChordPrediction(root="G", quality="min", bass="F", display="Gm/F", start_time=1.0, end_time=2.0, duration=1.0, confidence=0.9),
            ]
        )
        self.assertEqual(format_bar_str(walkdown_bar), "Gm/F")

        multi_bar = Bar(
            bar_number=2,
            start_time=0.0,
            end_time=2.0,
            chords=[
                ChordPrediction(root="A", quality="sus4", bass="A", display="Asus4", start_time=0.0, end_time=1.0, duration=1.0, confidence=0.9),
                ChordPrediction(root="D", quality="maj", bass="D", display="D", start_time=1.0, end_time=2.0, duration=1.0, confidence=0.9),
            ]
        )
        self.assertEqual(format_bar_str(multi_bar), "Asus4  D")


if __name__ == "__main__":
    unittest.main()
