# Storage, Audio Lifecycle & Data Retention

This document explains the physical storage architecture, audio handling, SQLite database models, and privacy considerations across Song Chord Analyzer.

---

## 1. Audio Storage Tiers & Data Boundaries

To prevent confusion between client devices and compute servers, audio files are explicitly categorized into four distinct tiers:

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                AUDIO DATA STORAGE TIERS                                 │
├──────────────────────┬──────────────────────┬──────────────────────┬────────────────────┤
│ 1. PHONE LOCAL AUDIO │ 2. SERVER TEMP AUDIO │ 3. MANAGED LIBRARY   │ 4. STEM CACHE      │
│ (User's Device)      │ (Upload Buffer)      │ (Host PC Library)    │ (Demucs Stems)     │
│ • User picks song    │ • Streamed via HTTP  │ • Saved after 100%   │ • Stored by SHA-256│
│ • Never modified     │ • %TEMP% / UUID dir  │ • %LOCALAPPDATA%/... │ • bass.wav &       │
│ • Stays on device    │ • Deleted on error   │ • Stored permanently │   other.wav        │
└──────────────────────┴──────────────────────┴──────────────────────┴────────────────────┘
```

1. **Phone Local Audio:** Original audio file stored on user's smartphone. The app reads bytes to transmit them over HTTP but never alters or deletes the user's source file.
2. **Server Temporary Audio:** Upload buffer on the host PC (`%TEMP%/SongChordAnalyzer/uploads/` or `STORAGE_DIR/temp/`). Streamed in 64 KB chunks up to 100 MB. Cleaned up automatically if analysis encounters a fatal error.
3. **Managed Library Audio:** Permanent storage on the host PC (`STORAGE_DIR/library/{song_id}/audio.<ext>`). Allows the desktop app and mobile app to stream audio playback via `GET /api/analysis/{id}/audio`.
4. **Separated Stems Cache:** Cached Demucs 4-stem separations in `STORAGE_DIR/stems/{audio_hash}/`. Keyed by SHA-256 audio content digest. Eliminates redundant stem separation if the same song is analyzed again.

---

## 2. Relational Database Schema (`database.sqlite`)

The backend tracks persistent library items in an embedded SQLite database located at:
`%LOCALAPPDATA%/SongChordAnalyzer/database.sqlite` (or `STORAGE_DIR/database.sqlite`).

### Table: `songs`
| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | `VARCHAR(64)` | `PRIMARY KEY` | 8-character unique analysis ID |
| `title` | `VARCHAR(255)` | `NOT NULL` | Song title |
| `artist` | `VARCHAR(255)` | `DEFAULT 'Unknown'` | Artist name |
| `duration` | `FLOAT` | `NOT NULL` | Duration in seconds |
| `key` | `VARCHAR(32)` | `NOT NULL` | Detected key tonic and mode (e.g. `"Bb Minor"`) |
| `tempo` | `FLOAT` | `NOT NULL` | Primary BPM (e.g. `86.1`) |
| `meter` | `VARCHAR(16)` | `NOT NULL` | Meter string (e.g. `"4/4"`, `"7/8"`) |
| `audio_path` | `TEXT` | `NOT NULL` | Path to managed audio file on host disk |
| `analysis_json`| `TEXT` | `NOT NULL` | Complete serialized `SongAnalysis` JSON contract |
| `is_favorite` | `BOOLEAN` | `DEFAULT 0` | User favorite flag |
| `created_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Initial analysis timestamp |
| `updated_at` | `DATETIME` | `DEFAULT CURRENT_TIMESTAMP` | Last modified timestamp |

---

## 3. Privacy & Data Handling Guarantees

1. **Where Audio is Stored:** Audio is stored strictly on the user's local smartphone and on the user's personal host laptop/PC.
2. **Third-Party Cloud Access:** **No third-party cloud service ever receives or stores audio files.** The Cloudflare Tunnel acts solely as an encrypted transit pipe; Cloudflare does not store audio data.
3. **Telemetry & Tracking:** Zero analytics, tracking cookies, or diagnostic pings are sent to external services.
