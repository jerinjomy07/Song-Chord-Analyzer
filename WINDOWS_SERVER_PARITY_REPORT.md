# Windows Engine <-> Server Parity Report

**Date:** 2026-10-07 00:43:31
**Song:** Bekhayali (Parity Test)
**Overall Result:** PASSED - 100% PARITY

## Parity Verification Metrics

| Metric | Expected (Windows Engine) | Actual (FastAPI Server) | Result |
| :--- | :--- | :--- | :--- |
| **Key Tonic** | `Bb` | `Bb` | **PASS** |
| **Key Mode** | `minor` | `minor` | **PASS** |
| **Key Display** | `Bb Minor` | `Bb Minor` | **PASS** |
| **Key Confidence** | `0.75` | `0.75` | **PASS** |
| **BPM** | `86.1` | `86.1` | **PASS** |
| **Meter Numerator** | `4` | `4` | **PASS** |
| **Meter Denominator** | `4` | `4` | **PASS** |
| **Meter Display** | `4/4` | `4/4` | **PASS** |
| **Beats Count** | `353` | `353` | **PASS** |
| **Beats Alignment (Max Diff)** | `< 0.01s` | `0.000000s` | **PASS** |
| **Downbeats Count** | `89` | `89` | **PASS** |
| **Downbeats Alignment (Max Diff)** | `< 0.01s` | `0.000000s` | **PASS** |
| **Chords Count** | `352` | `352` | **PASS** |
| **Chord Display Match %** | `100.0%` | `100.00%` | **PASS** |
| **Chord Root Match %** | `100.0%` | `100.00%` | **PASS** |
| **Chord Bass Match %** | `100.0%` | `100.00%` | **PASS** |
| **Chord Timing (Max Diff)** | `< 0.01s` | `0.000000s` | **PASS** |
| **Sections Count** | `11` | `11` | **PASS** |
| **Section Names Match** | `True` | `True` | **PASS** |
| **JSON Schema Conformance** | `True` | `True` | **PASS** |
| **Pydantic Deserialization** | `True` | `True` | **PASS** |

## Conclusion

Both the Windows desktop engine and the FastAPI server produce **identical musical analysis results** on the golden track. The server analysis engine is confirmed ready to serve as the authoritative single source of truth for the Android mobile client.
