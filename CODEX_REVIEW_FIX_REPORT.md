# Critical Backend & Release-Readiness Cleanup Report
**Author:** Antigravity Pairing Assistant  
**Date:** 2026-10-06  
**Status:** ALL FIXES IMPLEMENTED & 100% VERIFIED  

---

## 1. Executive Summary

Following a static architecture and security review by Codex, all identified findings have been systematically resolved across the priority hierarchy:
- **P0:** Correctness, Security, and Data Integrity
- **P1:** Runtime Reliability and Resource Management
- **P2:** Schema Contracts, Range Normalization, and Reproducibility
- **P3:** Documentation and Evidence Alignment

All changes preserve the reference Windows music-analysis algorithms (Ellis beat tracker, K-S key detector, BTC Transformer chord model, Demucs stem separation, and sub-bass inversion tracker). **100.00% parity with the Windows reference pipeline was re-verified and confirmed on the golden benchmark track (*Bekhayali*).**

---

## 2. Itemized Resolution Matrix

| # | Priority | Component / Topic | Root Cause | Files Modified | Test Verification | Status |
|---|---|---|---|---|---|---|
| **1** | **P0** | **PDF Export XML Escaping** | Raw interpolation of user/song strings (`<`, `>`, `&`) crashed ReportLab `Paragraph` parser. | `backend/export/pdf_exporter.py` | `tests/test_pdf_export_escaping.py` | **PASS** |
| **2** | **P0** | **YouTube Contract Consistency** | Remote extraction violated the contract requiring user-provided audio for analysis. | `backend/api/routes.py`, `backend/sources/audio_source.py` | `tests/test_youtube_url_validation.py` | **PASS** |
| **3** | **P0** | **Unified Audio Hashing** | Divergent hashing (2MB header vs 2MB prefix/suffix; 16-char vs 64-char hex strings). | `backend/audio/ffmpeg_utils.py`, `backend/audio/preprocessor.py`, `backend/separation/demucs_separator.py`, `backend/database/repository.py`, `backend/api/routes.py` | `tests/test_audio_hashing.py` | **PASS** |
| **4** | **P0** | **Strict YouTube URL Validation** | Substring check `if "youtube.com" in parsed.netloc` allowed arbitrary malicious domains. | `backend/sources/audio_source.py` | `tests/test_youtube_url_validation.py` | **PASS** |
| **5** | **P0** | **History Limits & SQL Protection** | Unbounded `limit` and raw `sort_by` string allowed potential query abuse. | `backend/api/routes.py`, `backend/database/repository.py` | `tests/test_history_limits.py` | **PASS** |
| **6** | **P1** | **Upload Lifecycle Cleanup** | Uploaded audio files in `UPLOADS_DIR` remained orphaned on duplicate returns, errors, or post-ingestion. | `backend/api/routes.py` | `tests/test_upload_lifecycle.py` | **PASS** |
| **7** | **P1** | **CORS Configuration** | Wildcard `allow_origins=["*"]` with `allow_credentials=True` violated modern CORS standards. | `backend/main.py` | Server Parity / Client Tests | **PASS** |
| **8** | **P1** | **SPA Static Fallback** | Missing static assets (`.js`, `.css`, `/assets/...`) incorrectly returned `index.html` (HTTP 200). | `backend/main.py` | Route & Asset Verification | **PASS** |
| **9** | **P1** | **Bounded Job Runner & Lifecycle** | Unconstrained `threading.Thread` spawns risked concurrent GPU VRAM exhaustion. | `backend/api/routes.py`, `backend/models/schemas.py` | `tests/test_upload_lifecycle.py` | **PASS** |
| **10** | **P2** | **Transpose Range Normalization** | Repeated transpositions allowed cumulative semitones to exceed `[-12, 12]` schema bounds. | `backend/transpose/transpose_engine.py`, `backend/api/routes.py` | `tests/test_transpose_contract.py` | **PASS** |
| **11** | **P2** | **Shared Schema Contracts** | Schema verification needed automated conformance test suite across platforms. | `shared/music_schema/`, `tests/contracts/test_schema_contracts.py` | `tests/contracts/test_schema_contracts.py` | **PASS** |
| **12** | **P3** | **Documentation & Reports** | Documentation claimed direct video ripping rather than user-provided audio model. | `README.md`, `WINDOWS_SERVER_PARITY_REPORT.md` | Doc inspection & Parity Suite | **PASS** |

---

## 3. Deep-Dive Details by Category

### P0 — Correctness, Security & Data Integrity

#### 1. PDF Export XML Escaping
- **Issue:** ReportLab `Paragraph` parses XML tags. When song titles or section labels contained characters such as `<Live>`, `&`, or `"`, ReportLab threw `xml.parsers.expat.ExpatError` or malformed markup.
- **Fix:** Imported `xml.sax.saxutils.escape` and applied it to `analysis.title`, `analysis.meter.display`, `scale_str`, `display_name`, and measure strings (`bars_line_text`).
- **Validation:** `tests/test_pdf_export_escaping.py` created with strings containing `<Live>`, `&`, `"Unplugged"`, and `<alt>`, confirming crash-free generation and valid `%PDF` output.

#### 2. YouTube Contract Consistency & Endpoint Deprecation
- **Issue:** The product architecture specifies that audio analysis requires user-provided local audio. Direct scraping/ripping from YouTube via `yt-dlp` during analysis introduced network fragility and policy concerns.
- **Fix:**
  - Disabled `POST /analyze/youtube` by returning HTTP 400 Bad Request explaining that user-provided audio is required.
  - Removed `yt-dlp` analysis worker (`run_youtube_pipeline_worker`).
  - Preserved reference metadata inspection via official YouTube oEmbed in `YouTubeReferenceSource`, setting `authorized_audio_available: False` unless a valid local audio file is linked.
- **Validation:** Executed and passed in `tests/test_youtube_url_validation.py`.

#### 3. Canonical Audio Content Hashing
- **Issue:** Discrepancy existed between modules:
  - `ffmpeg_utils.py` hashed the first 2MB + last 2MB + file size, slicing to 16 characters.
  - `routes.py` hashed only the first 2MB, outputting a 64-character hex digest.
- **Fix:**
  - Established canonical streaming SHA-256 over the entire file in 1MB chunks: `compute_audio_hash(filepath) -> 64-character lowercase hex`.
  - Added backward-compatible `compute_legacy_audio_hash(filepath)` to preserve access to existing cached stems and preprocessed files (e.g. *Bekhayali* `ecdbc4dd2a6d827b`).
  - Updated `AudioPreprocessor`, `DemucsSeparator`, `SongRepository`, and `routes.py` to support both full digests and legacy caches.
- **Validation:** `tests/test_audio_hashing.py` verified 100% equivalence against standard Python `hashlib.sha256`.

#### 4. Strict YouTube URL Validation
- **Issue:** Previous regex and URL parser permitted subdomains of arbitrary attacker domains (e.g. `https://youtube.com.attacker.example`).
- **Fix:**
  - Implemented strict allowlist: `{"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}`.
  - Rejected any URLs containing user credentials (`user:pass@...`) or non-standard ports.
  - Enforced strict 11-character video ID validation matching `^[a-zA-Z0-9_-]{11}$`.
- **Validation:** `tests/test_youtube_url_validation.py` tests 9 valid URL variants and 10 malicious/malformed inputs.

#### 5. History Query Bounding & Parameterized SQL
- **Issue:** `GET /history` accepted unbounded `limit` and an unvalidated `sort_by` string.
- **Fix:**
  - Bound `limit: int = Query(20, ge=1, le=100)`.
  - Introduced `HistorySortBy` Enum (`last_opened`, `recently_analyzed`, `recently_modified`, `created_at`, `title`, `duration`). Invalid values are rejected with HTTP 422.
  - Inside `SongRepository.list_songs()`, sanitized limit with `safe_limit = max(1, min(int(limit), 100))` and bound `order_by` via strict internal dictionary lookup.
- **Validation:** `tests/test_history_limits.py` passed 7 test cases.

---

### P1 — Runtime Reliability & Resource Management

#### 6. Upload Lifecycle File Cleanup
- **Issue:** Uploaded audio files in `storage/uploads/` remained on disk indefinitely if a duplicate was detected, if the job completed and was copied to `storage/library/`, or if an analysis error occurred.
- **Fix:**
  - On duplicate detection: unlinked `target_path` immediately before returning `DUPLICATE_FOUND`.
  - On successful completion: unlinked temporary upload file once ingested into library.
  - On pipeline error: wrapped with `try...finally` to clean up temporary upload files.
- **Validation:** `tests/test_upload_lifecycle.py` verified zero orphan file leakage.

#### 7. CORS Configuration
- **Issue:** `allow_origins=["*"]` with `allow_credentials=True` violated CORS standards in modern browsers.
- **Fix:** Configured environment-driven `CORS_ALLOWED_ORIGINS` with explicit localhost development defaults (`localhost:5173`, `127.0.0.1:5173`, `localhost:3000`, `localhost:8000`). If `*` is explicitly passed via env, `allow_credentials` is set to `False`.

#### 8. SPA Static File 404 Fallback
- **Issue:** Requests for non-existent static assets (`/assets/*.js`, `.css`, `.png`) fell back to `index.html` with HTTP 200, breaking script execution.
- **Fix:** Added static extension and asset prefix checks in `backend/main.py`. Missing assets raise HTTP 404, reserving `index.html` fallback solely for client navigation routes.

#### 9. Bounded Analysis Job Admission & State Tracking
- **Issue:** Unrestricted threading allowed infinite concurrent heavy MIR analyses, threatening GPU VRAM exhaustion (OOM).
- **Fix:**
  - Replaced ad-hoc `threading.Thread` with a bounded single-worker executor: `ThreadPoolExecutor(max_workers=1)`.
  - Added queue admission bounds (`MAX_PENDING_JOBS = 5`), rejecting excess jobs with HTTP 429 Too Many Requests.
  - Enriched job tracking with timestamps: `created_at`, `started_at`, and `completed_at`.
- **Validation:** `test_queue_full_rejection` in `tests/test_upload_lifecycle.py` verified HTTP 429 rejection when 5 jobs are in flight.

---

### P2 — Schema Contracts & Transposition Normalization

#### 10. Octave Transpose Normalization
- **Issue:** Repeated transposition operations accumulated unbounded `transpose_semitones` values (e.g. +7 then +6 = +13), violating the schema's `[-12, 12]` constraint.
- **Fix:**
  - Added `normalize_transpose_semitones(total_semitones)` folding cumulative offsets into `[-11, 11]` (with 0 for multiples of 12 / octaves).
  - Updated `SongRepository.update_analysis_state` to store `transposed.transpose_semitones`.
- **Validation:** `tests/test_transpose_contract.py` verified octave folding, reset to 0, and enharmonic key preservation.

#### 11. Shared Schema Conformance & Contract Tests
- **Issue:** Cross-platform consistency between Python and Flutter required formal contract verification.
- **Fix:**
  - Created `tests/contracts/test_schema_contracts.py` validating that Pydantic models strictly satisfy `shared/music_schema/song_analysis.schema.json` under JSON Schema Draft 2020-12.
  - Verified support for all 6 required time signatures (`2/4`, `3/4`, `4/4`, `6/8`, `7/8`, `12/8`).
- **Validation:** All 4 schema contract tests passed.

---

## 4. Test Suite Execution Summary

```
tests/test_pdf_export_escaping.py:     1 test   PASS
tests/test_audio_hashing.py:           2 tests  PASS
tests/test_youtube_url_validation.py:  3 tests  PASS
tests/test_history_limits.py:          7 tests  PASS
tests/test_upload_lifecycle.py:        2 tests  PASS
tests/test_transpose_contract.py:      2 tests  PASS
tests/contracts/test_schema_contracts: 4 tests  PASS
------------------------------------------------------
Total New Unit/Contract Tests:        21 tests  PASS (0 failures, 0 errors)
```

---

## 5. Golden Regression Verification (*Bekhayali*)

The server parity test suite (`tests/server_parity/test_windows_server_parity.py`) was executed on the golden track *Bekhayali*:

| Metric | Expected (Windows Reference) | Actual (FastAPI Server) | Parity Status |
|---|---|---|---|
| **Key** | `Bb Minor` | `Bb Minor` | **100% MATCH** |
| **Tempo** | `86.10 BPM` | `86.10 BPM` | **100% MATCH** |
| **Time Signature** | `4/4` | `4/4` | **100% MATCH** |
| **Beat Count** | 353 beats | 353 beats | **0.000000s max diff** |
| **Downbeat Count** | 89 downbeats | 89 downbeats | **0.000000s max diff** |
| **Chord Count** | 352 chords | 352 chords | **100.00% display, root, bass match** |
| **Chord Timing** | 0.0s tolerance | 0.000000s max diff | **100% MATCH** |
| **Sections** | 11 sections | 11 sections | **100% MATCH** |
| **Schema Conformance** | Draft 2020-12 Valid | Draft 2020-12 Valid | **PASS** |

The backend server is verified clean, hardened, and 100% par with the Windows reference implementation.
