"""
SQLite Database Layer for Song Chord Analyzer.
Provides thread-safe connections, automatic schema initialization,
integrity verification, corruption recovery, and WAL mode configuration.
Stored in Windows application data (%LOCALAPPDATA%\\SongChordAnalyzer\\database.sqlite).
"""

import sqlite3
import shutil
import time
from pathlib import Path
from typing import Optional
from backend.config import DB_PATH, STORAGE_DIR


SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS songs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    file_hash TEXT,
    duration REAL NOT NULL,
    format TEXT NOT NULL,
    audio_path TEXT NOT NULL,
    key_display TEXT NOT NULL,
    key_mode TEXT NOT NULL,
    bpm REAL NOT NULL,
    time_signature TEXT NOT NULL,
    transpose_value INTEGER DEFAULT 0,
    is_favorite INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_opened_at TEXT NOT NULL,
    model_version TEXT,
    pipeline_version TEXT,
    edit_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analyses (
    song_id TEXT PRIMARY KEY,
    analysis_data TEXT NOT NULL,
    raw_predictions TEXT,
    version INTEGER DEFAULT 1,
    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chord_corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    song_id TEXT NOT NULL,
    chord_index INTEGER NOT NULL,
    bar_number INTEGER NOT NULL,
    beat INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    original_model_chord TEXT NOT NULL,
    corrected_chord TEXT NOT NULL,
    root TEXT NOT NULL,
    quality TEXT NOT NULL,
    bass TEXT NOT NULL,
    inversion INTEGER NOT NULL,
    confidence_before REAL,
    source TEXT NOT NULL DEFAULT 'user',
    created_at TEXT NOT NULL,
    FOREIGN KEY(song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_songs_hash ON songs(file_hash);
CREATE INDEX IF NOT EXISTS idx_songs_updated ON songs(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_songs_last_opened ON songs(last_opened_at DESC);
CREATE INDEX IF NOT EXISTS idx_songs_fav ON songs(is_favorite);
CREATE INDEX IF NOT EXISTS idx_corrections_song ON chord_corrections(song_id);
"""


def verify_and_recover_db(db_path: Path = DB_PATH) -> None:
    """
    Verifies SQLite database existence and structural integrity on startup.
    If corruption is detected, preserves damaged database as backup and re-creates.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check;")
        result = cursor.fetchone()
        conn.close()
        if not result or result[0].lower() != "ok":
            raise sqlite3.DatabaseError(f"Integrity check returned: {result}")
    except Exception as e:
        timestamp = int(time.time())
        corrupt_backup = db_path.with_name(f"database.corrupted.{timestamp}.sqlite")
        print(f"[DB Warning] Database corruption detected ({e}). Backing up to {corrupt_backup}")
        try:
            shutil.copy2(db_path, corrupt_backup)
            db_path.unlink(missing_ok=True)
        except Exception as copy_err:
            print(f"[DB Error] Failed to backup corrupted database: {copy_err}")


def get_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Returns a SQLite connection with dict-like row factory and WAL mode."""
    conn = sqlite3.connect(str(db_path), timeout=15.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Path = DB_PATH) -> None:
    """Initializes schema and tables."""
    verify_and_recover_db(db_path)
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
        print(f"[DB] Initialized database at: {db_path}")
    finally:
        conn.close()


# Auto-initialize on module load
try:
    init_db()
except Exception as err:
    print(f"[DB Error] Failed to initialize database: {err}")
