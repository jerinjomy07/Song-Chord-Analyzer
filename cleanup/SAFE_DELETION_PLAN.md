# Safe Project Deletion Plan
**Baseline Project Size:** **6.27 GB** (6,730,782,109 bytes) across 23,894 files  
**Expected Size Reduction (Automated):** **4.51 GB** (4,847,127,561 bytes)  
**Expected New Project Size (Post-Automated):** **1.75 GB** (~1.73 GB, **72.4% reduction**)  

## 1. SAFE TO DELETE AUTOMATICALLY
These files and directories have been verified as purely generated build outputs, compilation caches, and temporary duplicate data that can be regenerated on demand or are obsolete logs.

| Path | Size | Category | Reason | Safe? |
|---|---:|---|---|:---:|
| `mobile/flutter_app/build` | 3.69 GB | F. REGENERABLE BUILD OUTPUT | Complete intermediate Flutter/Gradle build output directory (intermediates, debug APKs, duplicates). Rebuilt automatically on demand via flutter build. | **YES** |
| `mobile/flutter_app/.dart_tool/flutter_build` | 318.70 MB | G. CACHE / F. REGENERABLE BUILD OUTPUT | Compilation dill snapshots and kernel caches from past debug/test runs. Safely cleaned and recreated on build. | **YES** |
| `mobile/flutter_app/.dart_tool/hooks_runner` | 75.10 MB | G. CACHE | Temporary hook runner dill binaries. | **YES** |
| `dist_electron/win-unpacked` | 448.52 MB | F. REGENERABLE BUILD OUTPUT | Intermediate unpacked electron directory containing duplicated executables and ffmpeg. Rebuilt by npm run dist. | **YES** |
| `dist_electron/builder-debug.yml` | 6.12 KB | H. TEMPORARY DATA | Intermediate debug configuration dumped by electron-builder. | **YES** |
| `test_out.log` | 557.00 B | H. TEMPORARY DATA | Stale execution log from 24-Sep-26. Git-ignored. | **YES** |
| `test_err.log` | 0.00 B | H. TEMPORARY DATA | Stale empty log from 24-Sep-26. Git-ignored. | **YES** |
| `__pycache__` | 15.73 KB | G. CACHE | Root Python compiled bytecode directory. | **YES** |
| `.pytest_cache` | 5.61 KB | G. CACHE | Root pytest execution cache. | **YES** |
| `storage/__pycache__` | 16.73 KB | G. CACHE | Python bytecode cache in storage/. | **YES** |
| `storage/temp/bekhayali_golden_analysis.json` | 481.53 KB | I. DUPLICATE / H. TEMPORARY DATA | Exact byte-for-byte duplicate (SHA-256 1f3a3ad053e3...) of tracked file mobile/flutter_app/test/fixtures/bekhayali_golden_analysis.json. | **YES** |
| `storage/temp/regression_test` | 9.16 KB | H. TEMPORARY DATA | Stale temporary regression output from 24-Sep-26. | **YES** |
| **Subtotal (Automatic Safe Deletion)** | **4.51 GB** | | | |

## 2. SAFE TO ARCHIVE / NEEDS MY DECISION
These items are large build outputs or dependency trees. While regenerable via build scripts or package managers, they are currently functioning binaries or required for immediate offline execution. **They will NOT be deleted automatically** without explicit confirmation.

| Path | Size | Category | Reason | Safe? |
|---|---:|---|---|:---:|
| `dist_electron/SongChordAnalyzer-Setup.exe` | 142.78 MB | F. BUILD ARTIFACT (RELEASE INSTALLER) | Windows NSIS setup installer (07-Oct-26). Regenerable via npm run dist. Recommend preserving or archiving before deletion. | **NEEDS USER DECISION** |
| `dist_electron/SongChordAnalyzer.exe` | 142.57 MB | F. BUILD ARTIFACT (PORTABLE EXE) | Windows portable standalone executable (07-Oct-26). Regenerable via npm run dist. | **NEEDS USER DECISION** |
| `dist/android/SongChordAnalyzer-v1.0.0-release.apk` | 123.80 MB | F. BUILD ARTIFACT / J. LEGACY BUILD | Older release APK (v1.0.0 from 25-Sep). Current release APK is SongChordAnalyzer.apk at root. | **NEEDS USER DECISION** |
| `node_modules` | 542.85 MB | G. DEPENDENCY CACHE | Desktop/Electron root dependencies (542.85 MB). Regenerable via npm install, but required for local npm start/dist execution. | **NEEDS USER DECISION** |
| `frontend/node_modules` | 134.23 MB | G. DEPENDENCY CACHE | Vite/React frontend dependencies (134.23 MB). Regenerable via npm --prefix frontend install. | **NEEDS USER DECISION** |
| **Subtotal (Optional / Decision)** | **1.06 GB** | | | |

## 3. DO NOT DELETE (Strictly Protected Assets)
These files represent active source code, required ML weights, ground-truth reference audio, schema definitions, and production executables. Deleting any of these would break test suites, build pipelines, or application functionality.

| Path | Size | Category | Reason | Safe? |
|---|---:|---|---|:---:|
| `SongChordAnalyzer.apk` | 123.92 MB | F. CURRENT RELEASE ARTIFACT | The active, production-verified Android release APK (123.92 MB) containing the responsive 2-column chord sheet and 1-page PDF exporter. | **NO (DO NOT DELETE)** |
| `models/btc/btc_model.onnx` | 12.44 MB | B. REQUIRED MODEL ASSET | Pre-trained BTC chord inference ONNX model required by backend pipeline. | **NO (DO NOT DELETE)** |
| `models/btc/btc_model_large_voca.pt` | 11.66 MB | B. REQUIRED MODEL ASSET | PyTorch weights for large vocabulary BTC chord recognition. | **NO (DO NOT DELETE)** |
| `mobile/flutter_app/assets/models/btc_model_170voca.onnx` | 12.47 MB | B. REQUIRED MODEL ASSET | Quantized ONNX model bundled inside Android APK for offline mobile inference. | **NO (DO NOT DELETE)** |
| `mobile/android/native/inference/btc_model_170voca.onnx` | 12.47 MB | B. REQUIRED MODEL ASSET | Native Android C++ / JNI inference model asset. | **NO (DO NOT DELETE)** |
| `storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav` | 45.61 MB | C. REQUIRED TEST/REFERENCE DATA | Golden reference audio (Bekhayali 44.1kHz stereo) directly required by backend and server parity tests. | **NO (DO NOT DELETE)** |
| `storage/cache/ecdbc4dd2a6d827b_22k_mono.wav` | 11.40 MB | C. REQUIRED TEST/REFERENCE DATA | Golden reference audio (Bekhayali 22.05kHz mono) directly required by 7 Android parity tests. | **NO (DO NOT DELETE)** |
| `storage/cache/bekhayali_demo.mp3` | 6.21 MB | C. REQUIRED TEST/REFERENCE DATA | Golden benchmark audio for full song analysis and demo validation. | **NO (DO NOT DELETE)** |
| `storage/stems/ecdbc4dd2a6d827b` | 182.42 MB | C. REQUIRED TEST/REFERENCE DATA | Demucs separated stems (bass.wav, other.wav) used by parity benchmarks. | **NO (DO NOT DELETE)** |
| `storage/exports/test_analysis.json` | 664.07 KB | C. REQUIRED TEST/REFERENCE DATA | Golden analysis JSON required by test_pipeline_run.py and verify_features.py. | **NO (DO NOT DELETE)** |
| `resources/ffmpeg/ffmpeg.exe` | 155.73 MB | E. REQUIRED BUILD/RUNTIME INPUT | Bundled FFmpeg binary required by Windows backend audio processing. | **NO (DO NOT DELETE)** |
| `tools/cloudflared.exe` | 52.80 MB | E. REQUIRED BUILD/RUNTIME INPUT | Cloudflare tunnel binary required by scripts/start_tunnel.bat. | **NO (DO NOT DELETE)** |
| `build/app.ico` | 14.01 KB | E. REQUIRED BUILD INPUT | Windows application icon explicitly configured in electron-builder.yml. | **NO (DO NOT DELETE)** |
| `tests` | 13.50 MB | C. REQUIRED TEST DATA & CODE | Complete automated unit and parity test suite including golden WAV audio. | **NO (DO NOT DELETE)** |
| `backend` | 960.90 KB | A. REQUIRED SOURCE | Core MIR Python analysis pipeline and FastAPI server. | **NO (DO NOT DELETE)** |
| `mobile/flutter_app/lib` | 218.52 KB | A. REQUIRED SOURCE | Flutter cross-platform mobile application source code. | **NO (DO NOT DELETE)** |
| `electron` | 16.34 KB | A. REQUIRED SOURCE | Electron desktop shell implementation. | **NO (DO NOT DELETE)** |
| `frontend/src` | 183.27 KB | A. REQUIRED SOURCE | React/Vite web user interface source code. | **NO (DO NOT DELETE)** |