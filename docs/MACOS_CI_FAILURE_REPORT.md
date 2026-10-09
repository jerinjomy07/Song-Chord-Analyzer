# macOS CI Failure & Packaged App Validation Diagnostic Report
**Song Chord Analyzer — CI Run Failure Analysis & Verified Resolution**

---

## 1. Incident Overview

| Parameter | Run #13 (Failed Run) | Run #14 (Subsequent Green Run) |
| :--- | :--- | :--- |
| **Workflow** | `macOS Standalone Build & Parity Test` | `macOS Standalone Build & Parity Test` |
| **Branch** | `feature/macos-standalone` | `feature/macos-standalone` |
| **Run ID** | `37892386584` | `37893022279` |
| **Commit SHA** | `6ebd4b38acf24f3f231caabd601241b827aa3403` | `1e7459587bd46ccc460e1674919780ed2bfbc93c` |
| **Runner** | `macos-14` (Apple Silicon M1, ARM64) | `macos-14` (Apple Silicon M1, ARM64) |
| **Failed Step** | Step 16: `Execute Packaged Application Smoke & Parity Test` | *None (All 19 steps passed)* |
| **Step 16 Duration** | ~32s (Analysis finished in 10.37s, failed at assertion) | ~35s (100% verified) |
| **Report Upload** | Step 17 uploaded 0 bytes (no report file found) | Step 17 uploaded `macos-packaged-app-report` (1,690 B) |
| **Release Artifacts** | Step 18 skipped due to Step 16 exit code 1 | Step 18 uploaded `SongChordAnalyzer-macOS-arm64` (215.9 MB) |
| **Final Job Status** | **FAILURE (Exit Code 1)** | **SUCCESS (Exit Code 0)** |

---

## 2. Exact Failing Command & Raw Log Traceback (Run #13)

The failed run was triggered on commit `6ebd4b3`. Steps 1 through 15 (including Python core tests, macOS parity tests, frontend build, and Electron packaging) all passed successfully.

During Step 16 (`Execute Packaged Application Smoke & Parity Test`), the packaged backend launched, health check succeeded, and end-to-end analysis of *Bekhayali* (`storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav`) completed in 10.37 seconds. However, during result extraction for metric comparison, line 450 threw an uncaught `KeyError`:

```text
[Step 7/7] Executing Real Bundled Analysis on Golden Track via Local HTTP API...
[Analysis] Uploading ecdbc4dd2a6d827b_44k_stereo.wav (45.61 MB) to packaged server...
[Analysis] Job enqueued successfully. Analysis ID: 09a493b9
        Progress: 5% (PREPROCESSING) - Preprocessing audio for models...
        Progress: 52% (ANALYZING_BEATS) - Evaluating time signatures (2/4, 3/4, 4/4, 6/8, 7/8, 12/8) & downbeats...
        Progress: 65% (ANALYZING_CHORDS) - Extracting chord posterior probabilities from Original Mix...
        Progress: 80% (ANALYZING_INVERSION) - Analyzing sounding bass register for slash chords & inversions...
        Progress: 100% (COMPLETED) - Analysis complete!
      ✓ Packaged analysis completed in 10.37s!
      ✓ Result strictly conforms to shared/music_schema/song_analysis.schema.json!
    main()
  File "/Users/runner/work/Song-Chord-Analyzer/Song-Chord-Analyzer/tests/macos_parity/test_packaged_app.py", line 450, in main
    actual_bars = len(song_analysis_dict['beat_grid']['bars'])
                      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^
KeyError: 'bars'
##[error]Process completed with exit code 1.

##[group]Run actions/upload-artifact@v4
with:
  name: macos-packaged-app-report
  path: tests/macos_parity/macos_packaged_app_report.json
dist_electron/*.log
  if-no-files-found: ignore
No files were found with the provided path: tests/macos_parity/macos_packaged_app_report.json
dist_electron/*.log. No artifacts will be uploaded.
```

---

## 3. Root Cause Investigation

1. **Schema & Data Hierarchy Discrepancy:**
   - In [`shared/music_schema/song_analysis.schema.json`](file:///shared/music_schema/song_analysis.schema.json) and [`backend/models/schemas.py`](file:///backend/models/schemas.py), the `beat_grid` dictionary contains `beats` and `downbeats`.
   - Measures (`bars`) are defined hierarchically within each musical section:
     ```python
     bars_list = [bar for s in song_analysis_dict.get('sections', []) for bar in s.get('bars', [])]
     ```
   - Attempting direct access via `song_analysis_dict['beat_grid']['bars']` triggered `KeyError: 'bars'`.

2. **Uncaught Exception Preventing Report Generation:**
   - Because `test_packaged_app.py` previously had no `try...except` wrapper around the reporting logic, the uncaught exception at line 450 terminated the script before `macos_packaged_app_report.json` was written to disk.
   - Consequently, Step 17 (`Upload Packaged App Validation Report`) found no JSON report file to upload, giving the false appearance that the report had succeeded without producing any diagnostic artifact.
   - Step 18 (`Upload macOS Release Artifacts`) was skipped as a standard CI dependency gate.

---

## 4. Fix Applied & Verification

### 4.1 Fix Implementation
1. **Correct Data Extraction Paths:**
   - Corrected measure and chord extraction in `tests/macos_parity/test_packaged_app.py`:
     ```python
     actual_key = f"{song_analysis_dict['key']['tonic']} {song_analysis_dict['key']['mode']}"
     actual_bpm = song_analysis_dict['tempo']['bpm']
     actual_meter = song_analysis_dict['meter'].get('display', f"{song_analysis_dict['meter'].get('numerator', 4)}/{song_analysis_dict['meter'].get('denominator', 4)}")
     bars_list = [bar for s in song_analysis_dict.get('sections', []) for bar in s.get('bars', [])]
     actual_bars = len(bars_list)
     actual_sections = len(song_analysis_dict.get('sections', []))
     total_chords = len(song_analysis_dict.get('chords', []))
     ```
2. **Guaranteed Failure Report Persistence:**
   - Wrapped `test_packaged_app.py` execution in an exception-safe handler `save_report()`. If any unexpected error occurs, `macos_packaged_app_report.json` is guaranteed to be saved with `verdict: "FAILED"`, `error`, and `traceback`, ensuring CI always uploads diagnostics on failure.
3. **Electron Smoke Test Python Environment Override:**
   - Added `env_smoke["SONG_CHORD_ANALYZER_PYTHON"] = sys.executable` to guarantee the Electron launcher invokes the Python 3.11 environment with all project dependencies.

### 4.2 Verified Execution in Run #14 (`37893022279`)
All 19 steps in the workflow succeeded:
- Step 16: `Execute Packaged Application Smoke & Parity Test` **PASSED (✓)**
- Step 17: `Upload Packaged App Validation Report` **PASSED (✓)** — Artifact `11599028346`
- Step 18: `Upload macOS Release Artifacts` **PASSED (✓)** — Artifact `11599541908` (215,925,354 bytes)

---

## 5. Parity & Validation Metrics from Packaged Application

| Musical Metric | Expected (Windows Reference) | Actual (Packaged macOS App) | Agreement |
| :--- | :--- | :--- | :---: |
| **Audio Format** | 44,100 Hz, 2 Channels | 44,100 Hz, 2 Channels | **100% MATCH** |
| **Key & Mode** | `Bb minor` | `Bb minor` | **100.0%** |
| **Tempo / BPM** | 86.10 BPM | 86.10 BPM | **100.0% ($\Delta = 0.00$)** |
| **Primary Meter** | 4/4 | 4/4 | **100% MATCH** |
| **Bar / Measure Count** | 88 measures | 88 measures | **100% MATCH** |
| **Chord Event Count** | 352 chords | 352 chords | **100% MATCH** |
| **Root Pitch Accuracy** | 352 / 352 chords | 352 / 352 chords | **100.0%** |
| **Chord Quality Accuracy** | 352 / 352 chords | 352 / 352 chords | **100.0%** |
| **Bass / Inversion Accuracy** | 352 / 352 chords | 352 / 352 chords | **100.0%** |
| **Section Segmentation** | 11 sections | 11 sections | **100.0%** |
| **Schema Validation** | Adheres | Adheres to `song_analysis.schema.json` | **100% VALID** |

---

## 6. Generated Release Artifacts (Confirmed in Blob Storage)

| Artifact Name | Filename | Size (Bytes) | SHA-256 Checksum |
| :--- | :--- | :--- | :--- |
| **`SongChordAnalyzer-macOS-arm64`** | `SongChordAnalyzer-mac-arm64.dmg` | 109,809,391 | `afa32a4da7c0d899f6cacf975c2ccf7c4bb3163d7746d0f53ca25b8a8625b0af` |
| **`SongChordAnalyzer-macOS-arm64`** | `Song Chord Analyzer-0.1.7-arm64-mac.zip` | 106,424,436 | `2d48d551777cf500ef6e6c1919631ab29f4614a55bbd62fd250249a408668d72` |
| **`macos-packaged-app-report`** | `macos_packaged_app_report.json` | 1,690 | Recorded in Run #14 |
| **`macos-parity-report`** | `macos_parity_report.json` | 868 | Recorded in Run #14 |

---

## 7. Remaining Physical Device Limitations

1. **Gatekeeper Code Signing Bypass:**
   - Unsigned packages trigger Gatekeeper alerts. Bypass on macOS via:
     ```bash
     xattr -cr /Applications/SongChordAnalyzer.app
     ```
2. **CoreAudio Real-Time Playback:**
   - Physical audio latency, audio-chord synchronization, and scrub playback require testing with macOS audio hardware.
3. **Physical Offline Cold Launch:**
   - Confirm offline stem separation on physical Mac hardware without active Wi-Fi.
