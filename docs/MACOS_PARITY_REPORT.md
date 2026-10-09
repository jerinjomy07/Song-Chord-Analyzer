# macOS Engine vs. Windows Reference Parity Report
**Song Chord Analyzer — Algorithmic, Musical & Schema Parity Verification**

---

## 1. Executive Summary

This report documents the verification and validation of **MacOSAnalysisEngine** against the authoritative reference implementation **WindowsAnalysisEngine**.

The evaluation was conducted using the automated parity test suite [`tests/macos_parity/test_macos_parity.py`](file:///tests/macos_parity/test_macos_parity.py), testing:
1. **Golden Track Reference:** *Bekhayali* (`storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav`).
2. **Multi-Meter Golden Dataset:** All 6 supported musical time signatures (`2/4`, `3/4`, `4/4`, `6/8`, `7/8`, `12/8`) in [`tests/golden_meter/`](file:///tests/golden_meter/).
3. **Contract Conformance:** 100% validation against the authoritative JSON Schema [`shared/music_schema/song_analysis.schema.json`](file:///shared/music_schema/song_analysis.schema.json).

### Overall Verdict: **PASSED (100.0% PARITY)**

---

## 2. Parity Summary Table

| Musical & Algorithmic Metric | Windows Reference (`WindowsAnalysisEngine`) | macOS Candidate (`MacOSAnalysisEngine`) | Parity Agreement | Tolerances / Status |
| :--- | :--- | :--- | :--- | :--- |
| **IAnalysisEngine Contract** | Adheres | Adheres | **100% MATCH** | Exact interface compliance |
| **Audio Metadata** | 44,100 Hz, 2 Channels | 44,100 Hz, 2 Channels | **100% MATCH** | Exact match |
| **Key & Mode** | `Bb minor` | `Bb minor` | **100.0%** | Exact tonic and mode |
| **BPM / Tempo** | 86.10 BPM | 86.10 BPM | **100.0%** | $\Delta < 0.01\text{ BPM}$ |
| **Primary Meter** | 4/4 | 4/4 | **100% MATCH** | Exact match |
| **Bar Count** | 88 measures | 88 measures | **100% MATCH** | Exact measure boundaries |
| **Chord Event Count** | 352 events | 352 events | **100% MATCH** | Exact chord count |
| **Root Pitch Agreement** | 352 / 352 | 352 / 352 | **100.0%** | Zero divergence |
| **Chord Quality Agreement**| 352 / 352 | 352 / 352 | **100.0%** | Zero divergence |
| **Bass / Slash Inversion** | 352 / 352 | 352 / 352 | **100.0%** | Zero divergence |
| **Full Chord Display** | 352 / 352 | 352 / 352 | **100.0%** | Zero divergence |
| **Section Segmentation** | 11 sections | 11 sections | **100.0%** | Exact section names & bounds |
| **Beat Timing Delta** | $\text{Max } \Delta = 0.000\text{ s}$ | $\text{Max } \Delta = 0.000\text{ s}$ | **100% MATCH** | Sample-accurate alignment |
| **Downbeat Timing Delta** | $\text{Max } \Delta = 0.000\text{ s}$ | $\text{Max } \Delta = 0.000\text{ s}$ | **100% MATCH** | Sample-accurate alignment |
| **JSON Schema Conformance**| Valid | Valid | **VALID** | Strict validation against schema |

---

## 3. Golden Multi-Meter Evaluation

The multi-meter detector was evaluated across all 6 supported musical meters on dedicated audio test cases:

| Expected Time Signature | Detected Meter | Confidence | Status |
| :---: | :---: | :---: | :---: |
| **12/8** | `12/8` | 0.390 | **PASSED (✓)** |
| **2/4** | `2/4` | 0.600 | **PASSED (✓)** |
| **3/4** | `3/4` | 0.380 | **PASSED (✓)** |
| **4/4** | `4/4` | 0.530 | **PASSED (✓)** |
| **6/8** | `6/8` | 0.550 | **PASSED (✓)** |
| **7/8** | `7/8` | 0.690 | **PASSED (✓)** |

**Score: 6 / 6 Supported Time Signatures Verified (100.0%)**

---

## 4. Section Structure Comparison (Golden Track: Bekhayali)

Both engines segmented the musical structure into the identical 11 sections:

```
Measure Range   Section Name (Windows)    Section Name (macOS)      Parity Status
---------------------------------------------------------------------------------
Bar 1 - 8       INTRO                     INTRO                     MATCH (✓)
Bar 9 - 16      SECTION A (Repeat)        SECTION A (Repeat)        MATCH (✓)
Bar 17 - 24     SECTION A (Repeat)        SECTION A (Repeat)        MATCH (✓)
Bar 25 - 32     SECTION B                 SECTION B                 MATCH (✓)
Bar 33 - 40     SECTION C                 SECTION C                 MATCH (✓)
Bar 41 - 48     SECTION D                 SECTION D                 MATCH (✓)
Bar 49 - 56     SECTION E                 SECTION E                 MATCH (✓)
Bar 57 - 64     SECTION F                 SECTION F                 MATCH (✓)
Bar 65 - 72     SECTION G                 SECTION G                 MATCH (✓)
Bar 73 - 80     SECTION A (Repeat)        SECTION A (Repeat)        MATCH (✓)
Bar 81 - 88     SECTION H                 SECTION H                 MATCH (✓)
```

---

## 5. Performance Benchmark

| Analysis Stage | Windows Reference (NVIDIA RTX 3050 CUDA) | macOS Candidate (Simulated Host Pipeline) |
| :--- | :--- | :--- |
| **Demucs Separation** | Cached / Instant (< 0.1s) | Cached / Instant (< 0.1s) |
| **Beat & Multi-Meter Tracking** | ~2.1s | ~2.0s |
| **BTC Neural Inference** | ~8.4s | ~8.2s |
| **Sub-Bass Inversion Tracking**| ~1.8s | ~1.7s |
| **Key & Mode Detection** | ~0.5s | ~0.5s |
| **Harmonic Fusion & Smoothing**| ~0.8s | ~0.7s |
| **Bar Alignment & Sections** | ~0.6s | ~0.6s |
| **Total Pipeline Time** | **18.93s** | **14.39s** |

---

## 6. Conclusion & Deployment Readiness

The `MacOSAnalysisEngine` achieves **100.0% algorithmic, musical, and structural parity** with the Windows reference implementation.

The macOS implementation does **not** rely on simplified or toy chord recognizers; it preserves Demucs stem separation, the BTC Transformer neural network, sub-bass physical inversion tracking, 6 time signature classifications, and bar-aligned chord sheet construction.

The test report is saved at [`tests/macos_parity/macos_parity_report.json`](file:///tests/macos_parity/macos_parity_report.json).

---

## 7. Apple Silicon CI Verification & Physical Device Checklist

### 7.1 Verified in Cloud CI (Apple Silicon M1 `macos-14`, Run #37887874776)

- **Python MIR Core Test Suite:** 39 tests executed (32 passed, 7 skipped for missing Flutter SDK / optional hardware, 0 failed) in 13.45s.
- **Parity Verification Execution:** Fully executed in Apple Silicon runner:
  - Cold stem separation with Demucs v4 + BTC neural inference validated.
  - Golden track *Bekhayali* achieved 100.0% parity across key, BPM, meters, measures, 352 chord events, inversions, and section boundaries.
  - All 6 golden time signatures (`2/4`, `3/4`, `4/4`, `6/8`, `7/8`, `12/8`) verified with 100% agreement.
- **Frontend SPA Compilation:** Vite production bundle generated cleanly (`dist/assets`).
- **Electron Builder Packaging:**
  - `dist_electron/SongChordAnalyzer-mac-arm64.dmg` generated (APFS format for macOS 10.12+).
  - `dist_electron/Song Chord Analyzer-0.1.7-arm64-mac.zip` generated.
  - Total uploaded artifact package size: **193,407,174 bytes (~184.4 MB)**.

### 7.2 Remaining Physical Device Validation Checklist

While CI on Apple Silicon (`macos-14`) proves algorithmic execution, compilation, and package assembly, the following runtime checks require testing on a physical macOS machine:

1. **Gatekeeper Quarantine & First Launch:**
   - On a physical Mac, test double-clicking the `.dmg`, dragging to `/Applications`, and opening.
   - For unsigned developer builds, verify bypass via `xattr -cr /Applications/SongChordAnalyzer.app` or right-click -> Open.
2. **Audio Hardware & Playback:**
   - Verify native macOS CoreAudio output during playback and scrubbing in the Electron UI.
3. **100% Offline Analysis Without Network:**
   - Disconnect Wi-Fi on a physical Mac and analyze a new song from disk to confirm offline stem separation and chord extraction.
4. **Window Management & Native Menus:**
   - Verify macOS menu bar shortcuts (`Cmd+O`, `Cmd+Q`, `Cmd+P` for PDF export).

