# Testing, Verification & Parity Validation

This document catalogs the complete automated testing architecture, verification evidence, and parity proofs across Song Chord Analyzer.

---

## 1. Complete Test Suite Matrix

| Test Suite | Framework / Tool | Test File | Test Count | Current Status | Execution Time |
|---|---|---|:---:|:---:|:---:|
| **Python Backend Tests** | `unittest` / `pytest` | `tests/test_*.py` | **44 tests** | **100% PASS (OK)** | ~65s (CPU/CUDA) |
| **Flutter Mobile Tests** | `flutter test` | `mobile/flutter_app/test/` | **16 tests** | **100% PASS (OK)** | ~5s |
| **Flutter Code Analysis** | `flutter analyze` | `mobile/flutter_app/` | **0 issues** | **100% PASS** | ~10s |
| **Windows <-> FastAPI Parity**| Standalone runner | `tests/server_parity/test_windows_server_parity.py` | **21 checks** | **100% PARITY** | ~36s |
| **Golden Meter Regression**| `unittest` | `tests/test_golden_meter.py` | **10 songs** | **100% PASS** | ~15s |
| **Schema Contract Validation**| `pytest` | `tests/contracts/test_schema_contracts.py` | **8 contracts** | **100% PASS** | ~2s |
| **PDF Layout & Fit-to-Page**| `unittest` | `tests/test_mobile_pdf_layout.py` | **4 tests** | **100% PASS** | ~3s |

---

## 2. Parity Concept: Golden Fixture vs. Live Server Parity

It is essential to distinguish between the two levels of cross-platform parity:

1. **Golden Fixture Parity:** Validates that mobile and desktop UI components, serializers, transposition engines, and PDF exporters produce identical results when provided with identical input `SongAnalysis` data.
   - Tested in `mobile/flutter_app/test/golden_parity_test.dart`.
   - Result: 11/11 tests pass.
2. **Live End-to-End Parity:** Validates that running audio through the direct Windows desktop pipeline vs. uploading it over HTTP to the FastAPI server yields mathematically identical results.
   - Tested in `tests/server_parity/test_windows_server_parity.py`.
   - Result: 21/21 checks pass.

---

## 3. Authoritative Golden Parity Proof (*Bekhayali*)

On golden track *Bekhayali* (`storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav`), the direct Windows engine and the FastAPI server were executed back-to-back:

```
============================================================
WINDOWS ENGINE <-> FASTAPI SERVER PARITY VALIDATION
Target Song: Bekhayali (Parity Test)
Audio Path:  storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav
============================================================
[PASS] Key Tonic: expected=Bb, actual=Bb
[PASS] Key Mode: expected=minor, actual=minor
[PASS] Key Display: expected=Bb Minor, actual=Bb Minor
[PASS] Key Confidence: expected=0.75, actual=0.75
[PASS] BPM: expected=86.1, actual=86.1
[PASS] Meter Numerator: expected=4, actual=4
[PASS] Meter Denominator: expected=4, actual=4
[PASS] Meter Display: expected=4/4, actual=4/4
[PASS] Beats Count: expected=353, actual=353
[PASS] Beats Alignment (Max Diff): expected=< 0.01s, actual=0.000000s
[PASS] Downbeats Count: expected=89, actual=89
[PASS] Downbeats Alignment (Max Diff): expected=< 0.01s, actual=0.000000s
[PASS] Chords Count: expected=352, actual=352
[PASS] Chord Display Match %: expected=100.0%, actual=100.00%
[PASS] Chord Root Match %: expected=100.0%, actual=100.00%
[PASS] Chord Bass Match %: expected=100.0%, actual=100.00%
[PASS] Chord Timing (Max Diff): expected=< 0.01s, actual=0.000000s
[PASS] Sections Count: expected=11, actual=11
[PASS] Section Names Match: expected=True, actual=True
[PASS] JSON Schema Conformance: expected=True, actual=True
[PASS] Pydantic Deserialization: expected=True, actual=True
============================================================
RESULT: 100% PARITY ACHIEVED ACROSS ALL 21 METRICS
```

---

## 4. Multi-Meter Regression Suite (`tests/test_golden_meter.py`)

Every meter candidate was verified against ground-truth audio fixtures:
- `12_8`: Detected 12/8 (Expected: 12/8) — PASS
- `2_4`: Detected 2/4 (Expected: 2/4) — PASS
- `3_4`: Detected 3/4 (Expected: 3/4) — PASS
- `4_4`: Detected 4/4 (Expected: 4/4) — PASS
- `6_8`: Detected 6/8 (Expected: 6/8) — PASS
- `7_8`: Detected 7/8 (Expected: 7/8) — PASS
- `Bekhayali`: Detected 3/4 (Expected: 3/4) — PASS
- `Gagultha`: Detected 7/8 (Expected: 7/8) — PASS
- `Magale`: Detected 3/4 (Expected: 3/4) — PASS
- `Pavzhamalli`: Detected 2/4 (Expected: 2/4) — PASS
