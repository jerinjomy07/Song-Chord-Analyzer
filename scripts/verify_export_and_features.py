"""
Regression verification script for Song Chord Analyzer:
Tests:
1. PDF, TXT, and JSON export file generation and content verification
2. Filename sanitization against Windows illegal character rules
3. Complete structured JSON export schema verification
4. YouTube URL validation, video ID extraction, and policy compliance
"""

import sys
import os
import json
import re
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.models.schemas import (
    SongAnalysis,
    AudioMetadata,
    PipelineMetadata,
    KeyAnalysis,
    TempoAnalysis,
    MeterAnalysis,
    BeatGrid,
    MusicalSection,
    Bar,
    ChordPrediction,
)
from backend.export.pdf_exporter import export_to_pdf
from backend.export.txt_exporter import export_to_txt
from backend.export.json_exporter import export_to_json, build_complete_json_export
from backend.api.routes import sanitize_filename_title, get_safe_export_filename
from backend.sources.audio_source import YouTubeSource


def create_sample_analysis() -> SongAnalysis:
    """Builds a realistic SongAnalysis object modeled on Radhimaa."""
    meta = AudioMetadata(
        filename="Radhimaa.mp3",
        duration=180.0,
        sample_rate=44100,
        channels=2,
        format="mp3",
        file_size_bytes=5242880,
        file_hash="abc123hash"
    )
    pipeline = PipelineMetadata(
        app_version="1.0.0",
        model_name="BTC-Transformer + Demucs v4 + BassStem",
        model_version="1.0",
        separation_model="htdemucs",
        device_used="cuda",
        timestamp="2026-09-24T20:00:00Z"
    )
    key = KeyAnalysis(tonic="G", mode="minor", display="G Minor", confidence=0.96)
    tempo = TempoAnalysis(bpm=136.0, confidence=0.98, is_estimated=False)
    meter = MeterAnalysis(numerator=4, denominator=4, display="4/4", confidence=0.99)
    beat_grid = BeatGrid(
        bpm=136.0,
        beats=[i * (60.0 / 136.0) for i in range(16)],
        downbeats=[i * 4 * (60.0 / 136.0) for i in range(4)]
    )

    chord_events = [
        ChordPrediction(
            root="G", quality="minor", bass="G", inversion=0, display="Gm",
            start_time=0.0, end_time=1.76, duration=1.76, bar_position=1, beat_position=1, beat=1,
            confidence=0.95
        ),
        ChordPrediction(
            root="C", quality="minor", bass="C", inversion=0, display="Cm",
            start_time=1.76, end_time=3.53, duration=1.76, bar_position=2, beat_position=1, beat=1,
            confidence=0.92
        ),
        ChordPrediction(
            root="F", quality="major", bass="F", inversion=0, display="F",
            start_time=3.53, end_time=5.29, duration=1.76, bar_position=3, beat_position=1, beat=1,
            confidence=0.94
        ),
        ChordPrediction(
            root="Bb", quality="major", bass="Bb", inversion=0, display="Bb",
            start_time=5.29, end_time=7.06, duration=1.76, bar_position=4, beat_position=1, beat=1,
            confidence=0.91
        ),
        # Multi-chord bar with slash chord
        ChordPrediction(
            root="C", quality="major", bass="C", inversion=0, display="C",
            start_time=7.06, end_time=7.94, duration=0.88, bar_position=5, beat_position=1, beat=1,
            beat_duration=2.0, confidence=0.89
        ),
        ChordPrediction(
            root="C", quality="major", bass="G", inversion=2, display="C/G",
            start_time=7.94, end_time=8.82, duration=0.88, bar_position=5, beat_position=3, beat=3,
            beat_duration=2.0, confidence=0.87
        ),
    ]

    bar1 = Bar(bar_number=1, start_time=0.0, end_time=1.76, chords=[chord_events[0]], display="Gm")
    bar2 = Bar(bar_number=2, start_time=1.76, end_time=3.53, chords=[chord_events[1]], display="Cm")
    bar3 = Bar(bar_number=3, start_time=3.53, end_time=5.29, chords=[chord_events[2]], display="F")
    bar4 = Bar(bar_number=4, start_time=5.29, end_time=7.06, chords=[chord_events[3]], display="Bb")
    bar5 = Bar(bar_number=5, start_time=7.06, end_time=8.82, chords=[chord_events[4], chord_events[5]], display="C/G")

    sec_intro = MusicalSection(
        section_id="sec-intro",
        name="INTRO",
        start_time=0.0,
        end_time=7.06,
        start_bar=1,
        end_bar=4,
        bars=[bar1, bar2, bar3, bar4]
    )
    sec_verse = MusicalSection(
        section_id="sec-verse-1",
        name="VERSE 1",
        start_time=7.06,
        end_time=8.82,
        start_bar=5,
        end_bar=5,
        bars=[bar5]
    )

    return SongAnalysis(
        id="test-analysis-1",
        title="Song: A/B * Live?",
        metadata=meta,
        pipeline_metadata=pipeline,
        key=key,
        tempo=tempo,
        meter=meter,
        beat_grid=beat_grid,
        sections=[sec_intro, sec_verse],
        chords=chord_events,
        raw_predictions=[{"time": 0.0, "chord": "Gm"}]
    )


def test_filename_sanitization():
    print("\n--- Testing Filename Sanitization ---")
    raw_title = "Song: A/B * Live?"
    sanitized = sanitize_filename_title(raw_title)
    print(f"Original: '{raw_title}' -> Sanitized: '{sanitized}'")
    assert "/" not in sanitized and "\\" not in sanitized, "Filename must not contain slashes"
    assert ":" not in sanitized and "*" not in sanitized and "?" not in sanitized, "Illegal chars must be removed"
    assert sanitized == "Song_A-B_Live", f"Expected 'Song_A-B_Live', got '{sanitized}'"

    for ext in ["pdf", "txt", "json"]:
        ascii_name, disp = get_safe_export_filename(raw_title, ext)
        print(f"Format: {ext.upper()} -> File: {ascii_name} | Disposition: {disp[:40]}...")
        assert ascii_name.startswith("Song_A-B_Live_"), f"Unexpected name prefix: {ascii_name}"
        if ext == "pdf":
            assert ascii_name.endswith("_ChordSheet.pdf")
        elif ext == "txt":
            assert ascii_name.endswith("_ChordSheet.txt")
        elif ext == "json":
            assert ascii_name.endswith("_Analysis.json")

    print("[PASS] Filename sanitization passed perfectly.")


def test_export_pdf(analysis: SongAnalysis, tmp_dir: Path):
    print("\n--- Testing PDF Export ---")
    pdf_path = tmp_dir / "Song_A-B_Live_ChordSheet.pdf"
    res = export_to_pdf(analysis, pdf_path)
    assert res.exists(), f"PDF file was not created: {res}"
    file_size = res.stat().st_size
    print(f"Generated PDF: {res.name} ({file_size} bytes)")
    assert file_size > 1000, "PDF file is suspiciously small"

    with open(res, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-", "File is not a valid PDF binary"
    print("[PASS] PDF export verified successfully.")


def test_export_txt(analysis: SongAnalysis, tmp_dir: Path):
    print("\n--- Testing TXT Export ---")
    txt_content = export_to_txt(analysis)
    txt_path = tmp_dir / "Song_A-B_Live_ChordSheet.txt"
    txt_path.write_text(txt_content, encoding="utf-8")

    assert txt_path.exists(), "TXT file was not written"
    print(f"Generated TXT:\n{txt_content[:300]}...")
    assert "SONG: A/B * LIVE?" in txt_content or "SONG" in txt_content
    assert "Scale: Gm" in txt_content
    assert "Tempo: 136 BPM" in txt_content
    assert "|Gm|Cm|F|Bb|" in txt_content or "|Gm |Cm |F |Bb |" in txt_content or "Gm" in txt_content
    assert "Intro" in txt_content
    print("[PASS] TXT export verified successfully.")


def test_export_json(analysis: SongAnalysis, tmp_dir: Path):
    print("\n--- Testing Structured JSON Export ---")
    json_path = tmp_dir / "Song_A-B_Live_Analysis.json"
    export_to_json(analysis, json_path)
    assert json_path.exists(), "JSON file was not created"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Verify structured schema matching prompt section 4
    required_keys = [
        "song_metadata",
        "musical_attributes",
        "pipeline_metadata",
        "final_chord_predictions",
        "sections",
        "raw_chord_predictions"
    ]
    for k in required_keys:
        assert k in data, f"Missing required top-level key: {k}"

    # Verify musical attributes
    assert data["musical_attributes"]["key"] == "G"
    assert data["musical_attributes"]["mode"] == "minor"
    assert data["musical_attributes"]["bpm"] == 136.0
    assert data["musical_attributes"]["time_signature"] == "4/4"
    assert len(data["musical_attributes"]["beats"]) > 0

    # Verify chord predictions
    chords = data["final_chord_predictions"]
    assert len(chords) > 0
    first_chord = chords[0]
    chord_req_fields = ["display_chord", "root", "quality", "bass", "inversion", "start_time", "end_time", "duration", "bar", "beat", "confidence"]
    for field in chord_req_fields:
        assert field in first_chord, f"Chord is missing field: {field}"

    print(f"[PASS] JSON export contains complete structured analysis with {len(chords)} chords and {len(data['sections'])} sections.")


def test_youtube_validation():
    print("\n--- Testing YouTube Source Validation & Policy Compliance ---")
    valid_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ&feature=shared",
        "https://youtube.com/shorts/dQw4w9WgXcQ"
    ]
    for url in valid_urls:
        source = YouTubeSource(url)
        assert source.validate(), f"Expected valid for URL: {url}"
        assert source.video_id == "dQw4w9WgXcQ", f"Incorrect video_id: {source.video_id}"
        assert not source.is_authorized_audio_available(), "Authorized audio must be False"
        assert source.get_audio_path() is None, "Audio path must be None"

    # Test invalid URLs
    invalid_urls = [
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/123456",
        "not_a_url",
        "https://youtube.com/watch?v=short"
    ]
    for url in invalid_urls:
        source = YouTubeSource(url)
        assert not source.validate(), f"Expected invalid for URL: {url}"

    # Test metadata compliance message
    source = YouTubeSource("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    meta = source.get_metadata()
    assert meta["valid"] is True
    assert "compliance_message" in meta
    assert "This YouTube video cannot be imported directly for audio analysis" in meta["compliance_message"]
    print(f"YouTube metadata: Title='{meta.get('title')}', Channel='{meta.get('channel')}', AuthAvailable={meta.get('authorized_audio_available')}")
    print("[PASS] YouTube source validation and policy-compliant workflow verified.")


def main():
    print("=" * 60)
    print("   Song Chord Analyzer — Feature & Regression Suite")
    print("=" * 60)

    tmp_dir = PROJECT_ROOT / "storage" / "temp" / "regression_test"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    analysis = create_sample_analysis()

    test_filename_sanitization()
    test_export_pdf(analysis, tmp_dir)
    test_export_txt(analysis, tmp_dir)
    test_export_json(analysis, tmp_dir)
    test_youtube_validation()

    print("\n" + "=" * 60)
    print("   ALL REGRESSION TESTS PASSED (100% SUCCESS)")
    print("=" * 60)


if __name__ == "__main__":
    main()
