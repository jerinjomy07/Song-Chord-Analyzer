# Executed Validation Report

**Validation date:** 2026-10-07  
**Scope:** Windows desktop, FastAPI backend, shared schema, test sources under `tests/`, Python dependency installation, Windows/HTTP analysis parity, and Electron packaging.  
**Primary project review:** [PROJECT_REVIEW.md](PROJECT_REVIEW.md)

## Working-tree preservation

The initial Git state was captured before test execution in [validation_worktree_baseline.txt](validation_worktree_baseline.txt). The working tree already contained extensive backend, Flutter, Android parity, schema, packaging, and documentation changes. Existing mobile and Android work was retained; no reset, clean, commit, or user-data deletion was performed. Additional changes from other activity appeared during validation; the initial baseline and subsequent checkpoints distinguish the evolving tree. Validation outputs and changes are additive to that preserved state.

## Results at a glance

| Area | Result |
|---|---|
| Python tests in `tests/` | **57 passed** (`pytest tests -q`) |
| Backend/server parity, Bekhayali | **21/21 checks passed**; Windows engine and FastAPI produced equivalent output |
| Existing music meter regression cases | **Passed**; four real-song fixtures plus six synthetic cases |
| Shared schema contracts | **Passed**; backend output validates with JSON Schema and Pydantic |
| `flutter analyze` | **NOT CONFIGURED**; Flutter/Dart executable unavailable |
| Frontend production compile | **Passed** as part of `npm run dist` |
| JavaScript unit-test script | **NOT CONFIGURED**; no root `npm test` script |
| Full-repository test collection | **Blocked by unrelated stale tests** under `storage/` and root `test_btc.py`; details below |
| `npm run dist` | **Exit 0**; NSIS and portable artifacts exist; deprecated-signing/default-icon warnings resolved |
| Python clean environment | **Install/import passed** in a disposable Python 3.14 environment after NumPy version markers; requirements remain range-based, not locked |

## Findings, execution evidence, and corrections

### Upload path traversal

- **Reproducible?** No, through the actual FastAPI/Starlette multipart request path tested here. Starlette normalized traversal-shaped client filenames, and the route also stores a basename under a server-generated ID.
- **Correction:** No traversal-specific code change was needed. Added request-level regression coverage to prevent regressions.
- **Test:** `tests/test_upload_path_safety.py`.
- **Result:** Passed; no file was created outside the upload directory.
- **Limitation:** This does not claim the same behavior for alternate ASGI/multipart implementations that bypass Starlette parsing.

### Unbounded audio upload

- **Reproducible?** Yes. The upload path previously copied the complete body without an application-level size cap.
- **Root cause:** Unbounded `copyfileobj` into the temporary upload path.
- **Correction:** Uploads are now streamed in 1 MiB chunks and capped at 500 MiB; oversized requests return HTTP 413. The exception cleanup path removes the partially written file.
- **Regression test:** Oversized request with an 8-byte test cap, plus unexpected partial-write failure cleanup in `tests/test_upload_path_safety.py`.
- **Result:** Upload lifecycle group passed (**7 tests**); the full `tests/` suite passed (**57 tests**).

### PDF text escaping

- **Reproducible?** Yes. ReportLab interpreted text such as `<Live>` as markup and lost literal text. The first extraction regression also exposed that Python `.capitalize()` changed user section-name casing.
- **Root cause:** User-provided title/section text flowed into ReportLab `Paragraph` markup; section casing was altered during normalization.
- **Correction:** Escape untrusted PDF text and preserve the original casing after uppercasing only its first character.
- **Regression test:** `tests/test_pdf_export_escaping.py` extracts the generated PDF text and asserts literal angle brackets, ampersands, quotes, and ordinary text.
- **Result:** Passed.

### Audio hashing and duplicate identity

- **Reproducible?** Yes, the reviewed API and analysis paths used different identity schemes. The old static review’s precise description of the current implementation was stale: the current shared helper computes a streaming full-file SHA-256.
- **Root cause:** Inconsistent hash functions at earlier API/pipeline boundaries; historical cache names also use a legacy sampled hash.
- **Correction:** API duplicate checks and new analysis/cache metadata use `compute_audio_hash`; legacy hashing remains only to locate old cache/stem files.
- **Regression test:** `tests/test_audio_hashing.py` checks same bytes/same hash across filenames and detects differences after the first 2 MiB.
- **Result:** Passed.
- **Remaining limitation:** Existing database rows carrying only the old sampled hash may not be recognized by the new full-file lookup; no database-wide migration was attempted.

### Upload cleanup lifecycle

- **Reproducible?** Yes; temporary copies need cleanup on duplicate, invalid input, worker failure, and unexpected write failure.
- **Correction:** Cleanup behavior covers duplicate detection, exceptions/partial writes, successful ingestion, and analysis failure; managed library audio is retained.
- **Regression tests:** `tests/test_upload_lifecycle.py`, `tests/test_upload_worker_lifecycle.py`, and `tests/test_upload_path_safety.py`.
- **Result:** Passed. Success removes the temporary upload while retaining managed audio; failure paths leave no partial upload behind.

### CORS

- **Reproducible?** The tested configuration is explicit and does not reflect arbitrary origins; credentialed requests from the configured local origin work.
- **Correction:** Current allowlist comes from configured local origins/environment rather than wildcard reflection.
- **Regression test:** `tests/test_api_validation.py`.
- **Result:** Allowed origin accepted; untrusted origin rejected.

### Transpose bounds and malformed requests

- **Reproducible?** No failing API behavior in the supported request range; malformed and out-of-range inputs are rejected.
- **Regression tests:** `tests/test_transpose_contract.py` and API validation tests.
- **Result:** Passed, including API 422 responses for malformed/out-of-range inputs and shared contract bounds.

### History API limits and sorting

- **Reproducible?** Yes. Direct handler invocation exposed FastAPI `Query` objects as defaults rather than concrete values; route bounds were also required for client limits.
- **Root cause:** Query metadata used as a Python default in the direct call path.
- **Correction:** Use `Annotated` query validation with concrete defaults, constrained limits, and a fixed sort enum.
- **Regression tests:** `tests/test_history_limits.py`, `tests/test_history_library.py`.
- **Result:** Passed (**17 tests** in the focused history run); API validation is also covered in the full suite.

### Shared SongAnalysis schema

- **Reproducible?** Current backend output is schema-valid. Two legacy golden JSON snapshots lack `schema_version` and fail strict validation as stored fixtures.
- **Canonical representation:** Shared JSON Schema, mirrored by backend Pydantic models; no schema change was made to hide output errors.
- **Regression tests:** `tests/contracts/test_schema_contracts.py`; server parity validates actual API output through both JSON Schema and Pydantic.
- **Result:** Contract tests passed (**4 tests**); actual server output passed both validators.
- **Remaining limitation:** Flutter/Dart serialization was not executable here because Flutter is unavailable. Legacy fixture migration/backward-compatibility policy remains open.

### Analysis admission control and shutdown

- **Reproducible?** Yes. The prior static finding of per-request daemon threads was stale against the working tree at execution time, but atomic slot reservation needed validation.
- **Correction:** A single-worker `ThreadPoolExecutor`, five-job admission bound, atomic reservation/state creation, cleanup when admission/submission fails, and FastAPI shutdown draining are in place.
- **Regression test:** `tests/test_queue_admission.py` checks concurrent reservations; upload lifecycle tests cover queue-full rejection.
- **Result:** Passed. Concurrent attempts cannot reserve more than the configured bound.
- **Remaining limitation:** Job state is in-memory and does not survive process restarts; this implementation is for local/single-process operation.

### YouTube contract and user-facing flow

- **Reproducible?** Yes. The `/analyze/youtube` endpoint rejects direct downloading, while the frontend claimed it would extract audio and called that endpoint.
- **Root cause:** UI copy/action contradicted the reference-only source/API contract.
- **Correction:** UI now describes YouTube as a metadata/reference link and presents user-provided audio as required. Removed the direct extraction UI call path. Reference links and existing history association remain available. README already describes reference-first flow.
- **Regression/verification:** `tests/test_youtube_url_validation.py` and frontend TypeScript/Vite production build.
- **Result:** URL tests passed (**3 tests**); production frontend compiled.
- **Remaining limitation:** Legacy downloader/helper code remains in the backend source, but the supported API/UI flow does not expose direct YouTube audio analysis.

### Static asset fallback

- **Reproducible?** No for `/assets` paths: mounted static files return 404 for missing assets, rather than returning the SPA document.
- **Regression test:** `tests/test_api_validation.py` requests a missing `/assets` path.
- **Result:** Passed with 404. No fallback change was needed.

### Python dependency setup

- **Reproducible?** Partially. A root `requirements.txt` exists in the pre-existing working tree but uses version ranges rather than a fully pinned lock.
- **Root cause observed:** The original NumPy `<2` range attempted a source build on Python 3.14 and Torch import failed. This was isolated to a disposable venv.
- **Correction:** Added Python-version NumPy markers: NumPy 1.x below Python 3.13 and NumPy 2.x on Python 3.13+. A fresh environment install and imports succeeded for FastAPI, PyTorch/TorchAudio, librosa, soundfile, SciPy, Demucs, and ReportLab.
- **Result:** Clean environment install/import passed. Runtime packages were not added to desktop packaging by this change.
- **Remaining limitation:** Dependencies are not fully pinned; model downloads and GPU-specific Torch selection remain environment dependent.

### Electron packaging warnings

- **Reproducible?** Yes, the original build warned that `win.sign` was deprecated and that no app icon was set.
- **Correction:** Moved the no-op signing hook to `win.signtoolOptions.sign`. Generated `build/app.ico` from the existing frontend favicon and configured it for Windows packaging.
- **Test:** Final `npm run dist`.
- **Result:** Exit code 0. Build log had neither warning. NSIS installer and portable executable were generated:
  - `dist_electron/SongChordAnalyzer-Setup.exe`
  - `dist_electron/SongChordAnalyzer.exe`

### Documentation consistency

- **Reproducible?** Yes for YouTube claims: the UI contradicted the supported API and README flow.
- **Correction:** UI copy/action was aligned with reference-only metadata and upload-based analysis. The README’s reference-first description was retained.
- **Remaining limitation:** The README still contains broad product and licensing statements beyond what these tests independently establish.

## Executed test and build log

- `pytest tests -q`: **57 passed** in 63.09 seconds (final source/test state).
- Focused PDF extraction test: **1 passed**.
- Focused history tests: **17 passed**.
- Focused upload path/lifecycle/worker group: **7 passed**.
- Meter/music regression group: **26 passed**, including six synthetic fixtures and real tracks Bekhayali, Magale, Nallaru Po, and Pavzhamalli.
- YouTube URL tests: **3 passed**.
- Schema contract tests: **4 passed**.
- `npm run dist`: **exit code 0** after the final frontend/build configuration edits.
- `flutter analyze`: unavailable; no Flutter/Dart executable was found.
- `npm test`: not configured; package has no `test` script.
- Full-repository `pytest --collect-only -q`: blocked by stale/unrelated collection failures in `storage/test_pdf_style.py` and `storage/test_tight_pdf.py` (missing `pymupdf`) and root `test_btc.py` (missing `utils`). The maintained `tests/` suite passes.

## Windows engine versus local FastAPI parity

Ran both `WindowsAnalysisEngine.analyze()` and the real FastAPI upload/poll flow on `storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav` (Bekhayali) using a temporary data directory. Both returned:

- Key: **Bb minor**, confidence **0.75**
- Tempo: **86.1 BPM**
- Meter: **4/4**
- Beat/downbeat counts: **353 / 89**, maximum alignment difference **0.000000 s**
- Chords: **352**, display/root/bass match **100%**, timing maximum difference **0.000000 s**
- Sections: **11**, names identical
- Server output passed shared JSON Schema and Pydantic validation

Parity helper result: **21 checks passed, 0 failures**. The existing four real-song meter regressions also passed. This comparison establishes local Windows-engine/FastAPI equivalence for the tested track and current runtime; it does not establish Android runtime parity or cloud deployment readiness.

## Remaining work and limitations

- No Flutter analysis, Dart tests, or Android/Kotlin execution was possible because required SDK/CLI tools were not available.
- The repository-wide collector still encounters stale tests outside `tests/`.
- Python dependency ranges are not locked, and CUDA-specific reproducibility was not tested.
- Only the Bekhayali track received full Windows-engine/FastAPI output parity; the four other real songs were meter regression fixtures, not full chord-by-chord parity runs.
- No cloud deployment was attempted.
