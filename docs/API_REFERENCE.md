# FastAPI Server & REST API Reference

The Song Chord Analyzer backend exposes a REST API powered by **FastAPI 1.0.0** running on `http://0.0.0.0:8000`.

---

## 1. Authentication & Security Middleware

- **Optional API Key Authentication:** If the host sets the environment variable `API_AUTH_KEY` or `SONG_CHORD_ANALYZER_API_KEY`, the server enforces authentication across all data and analysis routes.
- **Header:** `X-API-Key: <secret_key>`
- **Exempt Paths:** `/health`, `/api/health`, `/docs`, `/openapi.json`, and `/assets/*` are exempt to allow diagnostic connection probes and static asset rendering.
- **Rejection:** Unauthorized requests receive `HTTP 401 Unauthorized` with JSON payload:
  ```json
  {"detail": "Unauthorized: Invalid or missing X-API-Key header"}
  ```

---

## 2. Complete Endpoint Specification

### 2.1 System Health & Hardware Diagnostics
- **Path:** `GET /api/health` (also aliased at `GET /health`)
- **Authentication:** None (Public diagnostic probe)
- **Response Schema (`HealthCheckResponse`):**
  ```json
  {
    "status": "healthy",
    "api_version": "1.0.0",
    "schema_version": "1.0.0",
    "analysis_engine": "WindowsAnalysisEngine (Authoritative MIR Pipeline)",
    "analysis_engine_available": true,
    "auth_required": false,
    "models_available": {
      "btc": true,
      "demucs": true
    },
    "device": "NVIDIA GeForce RTX 3050 6GB Laptop GPU",
    "cuda_available": true,
    "cpu_count": 16,
    "ram_total_gb": 15.7,
    "vram_free_mb": 5161.0,
    "vram_total_mb": 6143.5,
    "ffmpeg_path": "C:\...\resources\ffmpeg\ffmpeg.exe",
    "python_executable": "C:\...\python.exe"
  }
  ```

---

### 2.2 Submit Audio for Analysis
- **Path:** `POST /api/analyze`
- **Content-Type:** `multipart/form-data`
- **Request Parameters:**
  - `file`: Audio file binary (MP3, WAV, FLAC, M4A, AAC). Maximum size: **100 MB**.
  - `title` *(optional)*: String title override.
- **Admission Control:** If active in-flight analysis jobs $\ge 2$, returns `HTTP 503 Service Unavailable`:
  ```json
  {"detail": "Analysis queue is full (2 jobs in flight). Please wait for current analyses to complete."}
  ```
- **Response (`202 Accepted`):**
  ```json
  {
    "analysis_id": "b617036d",
    "status": "queued",
    "progress": 0,
    "current_stage": "QUEUED",
    "message": "Audio received successfully, queued for analysis...",
    "created_at": "2026-10-08T08:17:02.123456Z"
  }
  ```

---

### 2.3 Poll Analysis Job Status
- **Path:** `GET /api/analyze/{analysis_id}`
- **Path Parameter:** `analysis_id` (string UUID8).
- **Response (`AnalysisStatusResponse`):**
  ```json
  {
    "analysis_id": "b617036d",
    "status": "separating",
    "progress": 25,
    "current_stage": "SEPARATING",
    "message": "Separating stems with Demucs (Bass + Accompaniment)...",
    "created_at": "2026-10-08T08:17:02.123456Z",
    "started_at": "2026-10-08T08:17:02.456789Z",
    "completed_at": null,
    "error": null
  }
  ```
- **Possible `status` values:** `queued`, `preprocessing`, `separating`, `analyzing_beats`, `analyzing_chords`, `analyzing_inversion`, `analyzing_key`, `aligning_bars`, `detecting_sections`, `completed`, `failed`.

---

### 2.4 Retrieve Completed SongAnalysis
- **Path:** `GET /api/analysis/{analysis_id}`
- **Response:** Complete `SongAnalysis` JSON contract (see [DATA_SCHEMA.md](DATA_SCHEMA.md)).
- **Errors:** `HTTP 404 Not Found` if analysis ID does not exist or has not completed.

---

### 2.5 Audio Playback Streaming
- **Path:** `GET /api/analysis/{analysis_id}/audio`
- **Headers Supported:** `Range: bytes=start-end` (supports standard HTTP 206 Partial Content for audio seeking).
- **Content-Type:** `audio/mpeg` or `audio/wav`.
- **Side Effect:** Streams the ingested library audio file associated with `analysis_id`.

---

### 2.6 Server-Side Transposition
- **Path:** `POST /api/analysis/{analysis_id}/transpose`
- **Request Body (`TransposeRequest`):**
  ```json
  {
    "semitones": 2
  }
  ```
- **Response:** Transposed `SongAnalysis` object.

---

### 2.7 Song History & Library
- **`GET /api/history`:** Returns paginated list of all analyzed songs in SQLite.
- **`GET /api/history/recent`:** Returns recent analyzed songs (limit: 10).
- **`POST /api/history/{song_id}/favorite`:** Toggles favorite status.
- **`DELETE /api/history/{song_id}`:** Deletes song from database and managed audio library.

---

### 2.8 Server-Side Document Export
- **`GET /api/analysis/{analysis_id}/export/pdf`:** Returns binary PDF lead sheet formatted with ReportLab.
- **`GET /api/analysis/{analysis_id}/export/txt`:** Returns plain text musician chart.
- **`GET /api/analysis/{analysis_id}/export/json`:** Returns raw `SongAnalysis` JSON.
