# Executed Validation and Verified Cleanup Plan

> **For agentic workers:** Execute the stages in order. Preserve the captured working-tree baseline and follow the required test-first loop for code changes.

**Goal:** Validate the prior static review with existing tests and runtime evidence, then make only minimal fixes proven by reproducible failures.

**Architecture:** Run checks in an isolated Python environment first. Fix independent backend/API/export problems with narrow regression tests, then re-run tests, the Windows package build, and music/server parity checks. Keep all pre-existing mobile and analysis-engine work intact.

**Tech Stack:** Python 3.14 available on host, FastAPI/Pydantic, pytest/unittest, ReportLab, React/Vite/Electron, Flutter/Kotlin if tooling is available.

**Spec:** User-provided validation request in `C:/Users/jerin/.codex/attachments/fe9bd7c0-52e4-4e88-83fe-f87ce3c85eda/Pasted text.txt`.

## Global Constraints

- Do not reset, clean, or overwrite the existing working tree.
- Do not delete or rewrite `mobile/flutter_app` or Android parity changes.
- Do not alter core Windows music-analysis algorithms unless an executed regression proves an effect.
- Keep `npm run dist` working and verify final artifacts and exit status.
- Do not deploy or build another APK in this milestone.

## Review Focus

- User text containing XML metacharacters must export literally in PDFs.
- Hashes must represent full file content consistently, independent of filename.
- Rejected, duplicate, failed, and exceptional uploads must not leak temporary files.
- API bounds and CORS behavior must be explicit and tested.
- The shared schema must validate actual serialized `SongAnalysis` data.

---

### Task 1: Baseline preservation and test discovery

**Files:** `validation_worktree_baseline.txt`, `CODEX_EXECUTED_VALIDATION_REPORT.md`

- [x] Capture status before tests/edits.
- [ ] Discover and run all configured existing test suites; report unavailable toolchains as skipped/not configured.
- [ ] Determine backend dependency installation behavior in an isolated environment.

### Task 2: Narrow verified backend regressions

**Files:** `backend/export/pdf_exporter.py`, `backend/audio/ffmpeg_utils.py`, `backend/api/routes.py`, corresponding `tests/` files.

- [ ] Add and observe failing tests for PDF escaping, content hashing, and temporary upload lifecycle.
- [ ] Apply minimal fixes and rerun those tests plus the existing backend suite.

### Task 3: API, schema, lifecycle, and source contract

**Files:** backend API/models/config, shared schema, frontend/mobile serialization, API tests/docs.

- [ ] Reproduce CORS, range/bounds, malformed input, schema, and concurrency behaviors before changes.
- [ ] Align YouTube release claims with the user-provided-audio flow while preserving URL reference/history metadata.
- [ ] Implement only fixes supported by tests and keep music pipeline code out of scope.

### Task 4: Packaging and music/server parity

**Files:** `electron-builder.yml`, icon assets if suitable assets already exist, reports.

- [ ] Address Electron Builder warnings with minimal packaging changes where safe.
- [ ] Run the Bekhayali and existing music benchmarks, then the direct Windows engine versus local FastAPI comparison.
- [ ] Rerun `npm run dist`, confirm installer/portable artifacts and exit code 0.

### Task 5: Final report

- [ ] Record every finding's reproducibility, root cause, fix, regression test, result, and remaining limitation in `CODEX_EXECUTED_VALIDATION_REPORT.md`.
