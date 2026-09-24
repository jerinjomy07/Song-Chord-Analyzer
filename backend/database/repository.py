"""
Repository pattern for SQLite persistence in Song Chord Analyzer.
Handles songs, full analyses, chord corrections, search, duplicate detection,
library audio ingestion, and favorites.
"""

import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from backend.config import LIBRARY_DIR
from backend.database.db import get_connection
from backend.models.schemas import SongAnalysis


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SongRepository:
    @staticmethod
    def ingest_audio(song_id: str, source_audio_path: Path) -> Path:
        """
        Copies user audio into the application-managed song library.
        Prevents audio from becoming unusable if original file is moved or deleted.
        """
        song_dir = LIBRARY_DIR / song_id
        song_dir.mkdir(parents=True, exist_ok=True)
        ext = source_audio_path.suffix.lower() or ".mp3"
        dest_audio = song_dir / f"audio{ext}"

        if source_audio_path.resolve() != dest_audio.resolve():
            shutil.copy2(source_audio_path, dest_audio)

        return dest_audio

    @classmethod
    def save_analysis(
        cls,
        analysis: SongAnalysis,
        source_audio_path: Path,
        song_id: Optional[str] = None
    ) -> str:
        """
        Persists a newly completed song analysis into SQLite and the managed audio library.
        """
        sid = song_id or analysis.id or str(uuid.uuid4())[:8]
        analysis.id = sid

        # 1. Ingest audio into managed library
        managed_audio_path = cls.ingest_audio(sid, source_audio_path)
        analysis.audio_url = f"/api/analysis/{sid}/audio"

        now = now_iso()
        conn = get_connection()
        try:
            with conn:
                # Insert or update song record
                conn.execute(
                    """
                    INSERT INTO songs (
                        id, title, original_filename, file_hash, duration, format,
                        audio_path, key_display, key_mode, bpm, time_signature,
                        transpose_value, is_favorite, created_at, updated_at,
                        last_opened_at, model_version, pipeline_version, edit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        title = excluded.title,
                        duration = excluded.duration,
                        key_display = excluded.key_display,
                        key_mode = excluded.key_mode,
                        bpm = excluded.bpm,
                        time_signature = excluded.time_signature,
                        updated_at = excluded.updated_at,
                        last_opened_at = excluded.last_opened_at;
                    """,
                    (
                        sid,
                        analysis.title,
                        analysis.metadata.filename,
                        analysis.metadata.file_hash,
                        analysis.metadata.duration,
                        analysis.metadata.format,
                        str(managed_audio_path),
                        analysis.key.display,
                        analysis.key.mode,
                        analysis.tempo.bpm,
                        analysis.meter.display,
                        analysis.transpose_semitones,
                        0,
                        now,
                        now,
                        now,
                        analysis.pipeline_metadata.model_version,
                        analysis.pipeline_metadata.app_version,
                        0
                    )
                )

                # Insert or update analysis record
                analysis_json = analysis.model_dump_json()
                raw_pred_json = json.dumps(analysis.raw_predictions or [])
                conn.execute(
                    """
                    INSERT INTO analyses (song_id, analysis_data, raw_predictions, version)
                    VALUES (?, ?, ?, 1)
                    ON CONFLICT(song_id) DO UPDATE SET
                        analysis_data = excluded.analysis_data,
                        raw_predictions = excluded.raw_predictions;
                    """,
                    (sid, analysis_json, raw_pred_json)
                )

            print(f"[Repository] Successfully persisted song '{analysis.title}' (ID: {sid})")
            return sid
        finally:
            conn.close()

    @classmethod
    def get_song(cls, song_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves song metadata row."""
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM songs WHERE id = ?;", (song_id,))
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def get_analysis(cls, song_id: str) -> Optional[SongAnalysis]:
        """
        Loads full analysis from SQLite and updates last_opened_at.
        Instant opening without re-running audio analysis.
        """
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT a.analysis_data, s.audio_path, s.transpose_value, s.title
                FROM analyses a
                JOIN songs s ON s.id = a.song_id
                WHERE a.song_id = ?;
                """,
                (song_id,)
            )
            row = cur.fetchone()
            if not row:
                return None

            data = json.loads(row["analysis_data"])
            analysis = SongAnalysis.model_validate(data)
            analysis.id = song_id
            analysis.audio_url = f"/api/analysis/{song_id}/audio"
            analysis.transpose_semitones = row["transpose_value"]
            analysis.title = row["title"]

            # Update last_opened_at in background
            with conn:
                conn.execute(
                    "UPDATE songs SET last_opened_at = ? WHERE id = ?;",
                    (now_iso(), song_id)
                )

            return analysis
        finally:
            conn.close()

    @classmethod
    def find_by_file_hash(cls, file_hash: str) -> Optional[Dict[str, Any]]:
        """Duplicate detection: checks if an audio file with this hash was already analyzed."""
        if not file_hash:
            return None
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, title, key_display, bpm, time_signature, duration, created_at
                FROM songs
                WHERE file_hash = ?
                ORDER BY updated_at DESC
                LIMIT 1;
                """,
                (file_hash,)
            )
            row = cur.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @classmethod
    def list_songs(
        cls,
        query: Optional[str] = None,
        sort_by: str = "last_opened",
        favorites_only: bool = False,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Lists songs for the History page with search, filters, and sorting.
        """
        conn = get_connection()
        try:
            clauses = []
            params = []

            if favorites_only:
                clauses.append("is_favorite = 1")

            if query and query.strip():
                q = f"%{query.strip().lower()}%"
                clauses.append("(LOWER(title) LIKE ? OR LOWER(original_filename) LIKE ? OR LOWER(key_display) LIKE ?)")
                params.extend([q, q, q])

            where_str = f"WHERE {' AND '.join(clauses)}" if clauses else ""

            # Sort mapping
            order_by = {
                "last_opened": "last_opened_at DESC",
                "recently_analyzed": "created_at DESC",
                "recently_modified": "updated_at DESC",
                "title": "title ASC",
            }.get(sort_by, "last_opened_at DESC")

            sql = f"""
                SELECT id, title, original_filename, file_hash, duration, format,
                       key_display, key_mode, bpm, time_signature, transpose_value,
                       is_favorite, created_at, updated_at, last_opened_at,
                       model_version, pipeline_version, edit_count
                FROM songs
                {where_str}
                ORDER BY {order_by}
                LIMIT ?;
            """
            params.append(limit)

            cur = conn.cursor()
            cur.execute(sql, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @classmethod
    def get_recent_songs(cls, limit: int = 5) -> List[Dict[str, Any]]:
        """Fetches top recent songs for the Home screen quick access list."""
        return cls.list_songs(sort_by="last_opened", limit=limit)

    @classmethod
    def rename_song(cls, song_id: str, new_title: str) -> bool:
        """Renames a song entry in SQLite and within the cached analysis JSON."""
        title = new_title.strip()
        if not title:
            return False

        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE songs SET title = ?, updated_at = ? WHERE id = ?;",
                    (title, now_iso(), song_id)
                )
                cur = conn.cursor()
                cur.execute("SELECT analysis_data FROM analyses WHERE song_id = ?;", (song_id,))
                row = cur.fetchone()
                if row:
                    data = json.loads(row["analysis_data"])
                    data["title"] = title
                    conn.execute(
                        "UPDATE analyses SET analysis_data = ? WHERE song_id = ?;",
                        (json.dumps(data), song_id)
                    )
            return True
        finally:
            conn.close()

    @classmethod
    def toggle_favorite(cls, song_id: str) -> bool:
        """Toggles the is_favorite state (0 or 1). Returns new state."""
        conn = get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT is_favorite FROM songs WHERE id = ?;", (song_id,))
                row = cur.fetchone()
                if not row:
                    return False
                new_state = 1 if row["is_favorite"] == 0 else 0
                conn.execute(
                    "UPDATE songs SET is_favorite = ?, updated_at = ? WHERE id = ?;",
                    (new_state, now_iso(), song_id)
                )
                return bool(new_state)
        finally:
            conn.close()

    @classmethod
    def duplicate_song(cls, song_id: str) -> Optional[str]:
        """
        Duplicates an existing song analysis record into a new editable entry.
        Reuses the existing library audio file.
        """
        existing = cls.get_song(song_id)
        if not existing:
            return None

        analysis = cls.get_analysis(song_id)
        if not analysis:
            return None

        new_id = str(uuid.uuid4())[:8]
        new_title = f"{existing['title']} (Copy)"
        analysis.id = new_id
        analysis.title = new_title
        analysis.audio_url = f"/api/analysis/{new_id}/audio"

        now = now_iso()
        conn = get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO songs (
                        id, title, original_filename, file_hash, duration, format,
                        audio_path, key_display, key_mode, bpm, time_signature,
                        transpose_value, is_favorite, created_at, updated_at,
                        last_opened_at, model_version, pipeline_version, edit_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        new_id,
                        new_title,
                        existing["original_filename"],
                        existing["file_hash"],
                        existing["duration"],
                        existing["format"],
                        existing["audio_path"],
                        existing["key_display"],
                        existing["key_mode"],
                        existing["bpm"],
                        existing["time_signature"],
                        existing["transpose_value"],
                        0,
                        now,
                        now,
                        now,
                        existing["model_version"],
                        existing["pipeline_version"],
                        0
                    )
                )

                conn.execute(
                    "INSERT INTO analyses (song_id, analysis_data, raw_predictions, version) VALUES (?, ?, ?, 1);",
                    (new_id, analysis.model_dump_json(), json.dumps(analysis.raw_predictions or []))
                )
            return new_id
        finally:
            conn.close()

    @classmethod
    def delete_song(cls, song_id: str) -> bool:
        """
        Deletes a song from SQLite and cleans up its managed library files.
        Does NOT touch user external files outside of the application library.
        """
        conn = get_connection()
        try:
            with conn:
                conn.execute("DELETE FROM songs WHERE id = ?;", (song_id,))

            # Remove managed directory if present
            song_dir = LIBRARY_DIR / song_id
            if song_dir.exists():
                shutil.rmtree(song_dir, ignore_errors=True)

            return True
        finally:
            conn.close()

    @classmethod
    def record_chord_edit(
        cls,
        song_id: str,
        chord_index: int,
        original_chord: str,
        updated_chord: Any,
        bar_number: int,
        beat: int,
        updated_analysis: SongAnalysis
    ) -> bool:
        """
        Records a manual chord correction for machine-learning feedback tracking
        and updates the persistent analysis JSON and edit counter.
        """
        conn = get_connection()
        try:
            now = now_iso()
            with conn:
                # Log correction
                conn.execute(
                    """
                    INSERT INTO chord_corrections (
                        song_id, chord_index, bar_number, beat, start_time, end_time,
                        original_model_chord, corrected_chord, root, quality, bass,
                        inversion, confidence_before, source, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'user', ?);
                    """,
                    (
                        song_id,
                        chord_index,
                        bar_number,
                        beat,
                        updated_chord.start_time,
                        updated_chord.end_time,
                        original_chord,
                        updated_chord.display,
                        updated_chord.root,
                        updated_chord.quality,
                        updated_chord.bass,
                        updated_chord.inversion,
                        updated_chord.confidence,
                        now
                    )
                )

                # Update analysis JSON and song edit_count
                conn.execute(
                    "UPDATE analyses SET analysis_data = ? WHERE song_id = ?;",
                    (updated_analysis.model_dump_json(), song_id)
                )
                conn.execute(
                    "UPDATE songs SET edit_count = edit_count + 1, updated_at = ? WHERE id = ?;",
                    (now, song_id)
                )
            return True
        except Exception as e:
            print(f"[Repository] Error recording chord edit: {e}")
            return False
        finally:
            conn.close()

    @classmethod
    def update_analysis_state(
        cls,
        song_id: str,
        updated_analysis: SongAnalysis,
        transpose_value: Optional[int] = None
    ) -> bool:
        """Updates analysis JSON and optionally transpose value in SQLite."""
        conn = get_connection()
        try:
            now = now_iso()
            with conn:
                conn.execute(
                    "UPDATE analyses SET analysis_data = ? WHERE song_id = ?;",
                    (updated_analysis.model_dump_json(), song_id)
                )
                if transpose_value is not None:
                    conn.execute(
                        "UPDATE songs SET transpose_value = ?, updated_at = ? WHERE id = ?;",
                        (transpose_value, now, song_id)
                    )
                else:
                    conn.execute(
                        "UPDATE songs SET updated_at = ? WHERE id = ?;",
                        (now, song_id)
                    )
            return True
        finally:
            conn.close()
