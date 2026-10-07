# Project Review — Execution Addendum

The earlier static review has been updated after execution. See [CODEX_EXECUTED_VALIDATION_REPORT.md](CODEX_EXECUTED_VALIDATION_REPORT.md) for test evidence and per-finding results.

## Findings corrected or bounded by execution

- Upload filename traversal was **not reproduced** through the FastAPI/Starlette multipart path; filenames are normalized and the route stores a basename under an analysis ID.
- An actual upload size limit was missing. The route now streams in 1 MiB chunks and rejects uploads above 500 MiB with 413.
- PDF user text was interpreted as markup; escaping plus section-case preservation now passes a PDF text-extraction regression test.
- Upload and pipeline hashing now share full-file streaming SHA-256 for new identity; legacy sampled hashes remain for locating older caches. Old DB hash compatibility remains a migration limitation.
- Duplicate/temp upload cleanup, queue admission, CORS, history bounds, transpose validation, YouTube URL parsing, API error cases, and shared schema have execution coverage. `pytest tests -q`: 57 passed.
- The `/assets` fallback concern was not reproduced: missing mounted static assets return 404.
- The API disabled direct YouTube analysis while the frontend promised it. UI action/copy now require a user-provided audio file while retaining YouTube metadata/reference links.
- Electron signing/icon warnings were corrected; final `npm run dist` succeeded and produced the NSIS installer and portable executable.
- Bekhayali Windows engine/FastAPI parity passed 21/21 checks. Four real-song meter regressions also passed.

## Tooling limitations

`flutter analyze` could not run because Flutter/Dart is unavailable. `npm test` is not configured. The full repository test collector sees stale collection errors under `storage/` (missing `pymupdf`) and root `test_btc.py` (missing `utils`); the maintained `tests/` suite passes. See the executed report for details and remaining limitations.
