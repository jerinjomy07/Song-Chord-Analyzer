"""
Integration tests for the SQLite Persistent History & Song Library System.
Verifies repository operations, instant reload, duplicate detection,
manual edit tracking, audio file lifecycle, and API endpoints.
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import STORAGE_DIR, LIBRARY_DIR
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
    ChordPrediction
)
from backend.database.repository import SongRepository
from backend.database.db import get_connection


def create_sample_analysis(song_id: str = "test-song-1", title: str = "Autumn Leaves") -> SongAnalysis:
    """Creates a realistic dummy SongAnalysis for testing."""
    sample_chord = ChordPrediction(
        root="C",
        quality="maj",
        bass="C",
        inversion=0,
        display="C",
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        confidence=0.95,
        needs_review=False,
        alternatives=[]
    )
    sample_bar = Bar(
        bar_number=1,
        start_time=0.0,
        end_time=2.0,
        chords=[sample_chord],
        time_signature="4/4",
        display="|C|"
    )
    sample_section = MusicalSection(
        section_id="intro-1",
        name="Intro",
        start_time=0.0,
        end_time=2.0,
        start_bar=1,
        end_bar=1,
        bars=[sample_bar],
        is_repeated=False
    )
    return SongAnalysis(
        id=song_id,
        title=title,
        metadata=AudioMetadata(
            filename=f"{title.replace(' ', '_')}.mp3",
            duration=120.5,
            sample_rate=44100,
            channels=2,
            format="mp3",
            file_size_bytes=1024000,
            file_hash="mockhash1234567890abcdef"
        ),
        pipeline_metadata=PipelineMetadata(
            app_version="1.0.0",
            model_name="BTC-Large",
            model_version="1.0",
            separation_model="htdemucs",
            device_used="cuda",
            timestamp="2026-09-24T12:00:00Z"
        ),
        key=KeyAnalysis(tonic="C", mode="major", display="C Maj", confidence=0.98),
        tempo=TempoAnalysis(bpm=120.0, confidence=0.95, is_estimated=False),
        meter=MeterAnalysis(numerator=4, denominator=4, display="4/4", confidence=1.0, is_estimated=False),
        beat_grid=BeatGrid(bpm=120.0, beats=[0.0, 0.5, 1.0, 1.5], downbeats=[0.0]),
        sections=[sample_section],
        chords=[sample_chord],
        transpose_semitones=0,
        has_stems=False
    )


def test_repository_save_and_retrieve():
    """Test saving a song analysis to SQLite and retrieving it instantly."""
    analysis = create_sample_analysis("song-001", "Autumn Leaves")
    
    # Create a temporary dummy audio file to ingest
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        f.write(b"dummy audio content for testing 12345")
        temp_audio = Path(f.name)

    try:
        saved_id = SongRepository.save_analysis(analysis, temp_audio, "song-001")
        assert saved_id == "song-001"

        # Verify instant retrieval without re-running analysis
        retrieved = SongRepository.get_analysis("song-001")
        assert retrieved is not None
        assert retrieved.id == "song-001"
        assert retrieved.title == "Autumn Leaves"
        assert retrieved.key.display == "C Maj"
        assert retrieved.tempo.bpm == 120.0
        assert len(retrieved.chords) == 1
        assert retrieved.chords[0].display == "C"

        # Verify managed audio exists in library
        song_row = SongRepository.get_song("song-001")
        assert song_row is not None
        assert Path(song_row["audio_path"]).exists()
        assert song_row["file_hash"] == "mockhash1234567890abcdef"

    finally:
        if temp_audio.exists():
            temp_audio.unlink()


def test_duplicate_detection_by_hash():
    """Test finding previously analyzed song by audio content hash."""
    found = SongRepository.find_by_file_hash("mockhash1234567890abcdef")
    assert found is not None
    assert found["id"] == "song-001"
    assert found["title"] == "Autumn Leaves"

    # Non-existent hash should return None
    assert SongRepository.find_by_file_hash("nonexistenthash") is None


def test_list_songs_and_search():
    """Test searching and sorting library songs."""
    songs = SongRepository.list_songs(query="Autumn", sort_by="title")
    assert len(songs) >= 1
    assert any(s["id"] == "song-001" for s in songs)

    # Empty match
    assert len(SongRepository.list_songs(query="XYZNonExistentSong1234")) == 0


def test_toggle_favorite():
    """Test toggling favorite status."""
    is_fav = SongRepository.toggle_favorite("song-001")
    assert is_fav is True
    fav_songs = SongRepository.list_songs(favorites_only=True)
    assert any(s["id"] == "song-001" for s in fav_songs)

    # Toggle off
    is_fav = SongRepository.toggle_favorite("song-001")
    assert is_fav is False


def test_rename_song():
    """Test renaming a song in library and JSON analysis."""
    success = SongRepository.rename_song("song-001", "Autumn Leaves (Remastered)")
    assert success is True

    song = SongRepository.get_song("song-001")
    assert song["title"] == "Autumn Leaves (Remastered)"

    analysis = SongRepository.get_analysis("song-001")
    assert analysis.title == "Autumn Leaves (Remastered)"


def test_manual_chord_edit_and_transpose_persistence():
    """Test recording manual chord edit and transpose persistence in SQLite."""
    analysis = SongRepository.get_analysis("song-001")
    target_chord = analysis.chords[0]
    
    # Edit chord
    SongRepository.record_chord_edit(
        song_id="song-001",
        chord_index=0,
        original_chord=target_chord.display,
        updated_chord=target_chord,
        bar_number=1,
        beat=1,
        updated_analysis=analysis
    )

    song = SongRepository.get_song("song-001")
    assert song["edit_count"] >= 1

    # Transpose state update
    analysis = SongRepository.get_analysis("song-001")
    analysis.transpose_semitones = 2
    SongRepository.update_analysis_state("song-001", analysis, transpose_value=2)

    song = SongRepository.get_song("song-001")
    assert song["transpose_value"] == 2


def test_duplicate_song_record():
    """Test cloning a song analysis into a new library entry."""
    new_id = SongRepository.duplicate_song("song-001")
    assert new_id is not None
    assert new_id != "song-001"

    dup_song = SongRepository.get_song(new_id)
    assert dup_song is not None
    assert "(Copy)" in dup_song["title"]

    # Cleanup duplicate
    SongRepository.delete_song(new_id)


import asyncio
from backend.api import routes


def test_api_history_endpoints():
    """Test FastAPI history route handlers directly."""
    # 1. GET /api/history
    songs = asyncio.run(routes.list_history_songs())
    assert isinstance(songs, list)
    assert len(songs) >= 1

    # 2. GET /api/history/recent
    recent = asyncio.run(routes.list_recent_songs(limit=3))
    assert isinstance(recent, list)
    assert len(recent) <= 3

    # 3. GET /api/history/{id}/open (Instant open without analysis)
    analysis = asyncio.run(routes.open_song_from_history("song-001"))
    assert analysis.id == "song-001"
    assert "Autumn Leaves" in analysis.title

    # 4. PATCH /api/history/{id}/rename
    rename_res = asyncio.run(routes.rename_song_entry("song-001", routes.RenameSongRequest(title="Autumn Leaves - Jazz Standard")))
    assert rename_res["success"] is True
    assert rename_res["title"] == "Autumn Leaves - Jazz Standard"

    # 5. POST /api/history/{id}/favorite
    fav_res = asyncio.run(routes.toggle_song_favorite("song-001"))
    assert fav_res["success"] is True
    assert "is_favorite" in fav_res

    # 6. POST /api/history/{id}/duplicate
    dup_res = asyncio.run(routes.duplicate_song_entry("song-001"))
    assert dup_res["success"] is True
    new_song_id = dup_res["new_song_id"]

    # 7. DELETE duplicate
    del_res = asyncio.run(routes.delete_song_entry(new_song_id))
    assert del_res["success"] is True


def test_delete_and_library_cleanup():
    """Test deleting song removes row and managed audio directory."""
    song = SongRepository.get_song("song-001")
    audio_path = Path(song["audio_path"])
    parent_dir = audio_path.parent

    success = SongRepository.delete_song("song-001")
    assert success is True
    assert SongRepository.get_song("song-001") is None
    assert SongRepository.get_analysis("song-001") is None
    # Managed directory deleted
    assert not parent_dir.exists()


if __name__ == "__main__":
    print("Running History & Library System Integration Tests...")
    test_repository_save_and_retrieve()
    print("[OK] test_repository_save_and_retrieve passed")
    test_duplicate_detection_by_hash()
    print("[OK] test_duplicate_detection_by_hash passed")
    test_list_songs_and_search()
    print("[OK] test_list_songs_and_search passed")
    test_toggle_favorite()
    print("[OK] test_toggle_favorite passed")
    test_rename_song()
    print("[OK] test_rename_song passed")
    test_manual_chord_edit_and_transpose_persistence()
    print("[OK] test_manual_chord_edit_and_transpose_persistence passed")
    test_duplicate_song_record()
    print("[OK] test_duplicate_song_record passed")
    test_api_history_endpoints()
    print("[OK] test_api_history_endpoints passed")
    test_delete_and_library_cleanup()
    print("[OK] test_delete_and_library_cleanup passed")
    print("\nALL 9 HISTORY & SONG LIBRARY TESTS PASSED PERFECTLY!")
