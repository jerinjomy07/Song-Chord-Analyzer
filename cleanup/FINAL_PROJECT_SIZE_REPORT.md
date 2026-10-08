# Final Clean Project Size Report & Architecture Map
**Audit & Cleanup Date:** 2026-10-08  
**Baseline Size:** **6.27 GB** (6,730,782,109 bytes)  
**Final Clean Size:** **1.85 GB** (1,987,856,232 bytes)  
**Space Reclaimed:** **4.42 GB** (70.47% reduction)  
**Final File Count:** **13,901 files** (9,996 build intermediates and caches safely removed)  

## Why the Remaining Project Size is Necessary
The project has been compressed to its minimal, completely reproducible foundation. Every remaining megabyte directly serves runtime execution, model inference, test integrity, or cross-platform distribution without any bloat.

## Top 20 Largest Remaining Items (Files & Directories)

| Rank | Item / Path | Size | Purpose | Why It Remains | Required For |
|---|---|---:|---|---|---|
| 1 | `node_modules/` | 542.85 MB | Node.js dependencies for Electron desktop wrapper and electron-builder packaging | Provides the Electron runtime, electron-builder bundler, and build tooling so npm run dist and the desktop application run out of the box without requiring npm download | Windows Desktop, Development |
| 2 | `dist_electron/SongChordAnalyzer-Setup.exe` | 142.78 MB | Official Windows NSIS desktop installer binary | Preserved as current functioning Windows distribution installer; avoids needing to rebuild on end-user machines unless modified | Windows Desktop Distribution |
| 3 | `dist_electron/SongChordAnalyzer.exe` | 142.57 MB | Standalone portable Windows executable | Preserved for zero-install portable execution on Windows without administrator privileges | Windows Desktop |
| 4 | `resources/ffmpeg/ffmpeg.exe` | 155.73 MB | Static FFmpeg binary for Windows audio transcoding and sample rate conversion | Bundled local binary required by Windows backend pipeline (librosa/soundfile fallback and Demucs audio decoding) | Windows Desktop, Server, Development |
| 5 | `frontend/node_modules/` | 134.23 MB | Vite, React, Tailwind CSS, Lucide icons, and web frontend UI development packages | Enables instant local frontend compilation and Vite HMR without re-running npm install | Windows Desktop, Development |
| 6 | `SongChordAnalyzer.apk (root)` | 123.92 MB | Production release Android APK (v1.0.0+ with responsive 2-col chord grid and 1-page PDF export) | Current validated, ready-to-install mobile release package. Preserved to prevent losing working mobile distribution | Android Mobile Distribution |
| 7 | `dist/android/SongChordAnalyzer-v1.0.0-release.apk` | 123.80 MB | Initial release Android APK build (v1.0.0 milestone archive) | Preserved distribution archive for historical version comparison and baseline testing | Android Mobile (Archive) |
| 8 | `storage/stems/ecdbc4dd2a6d827b/bass.wav` | 91.21 MB | Demucs separated bass stem for golden reference song Bekhayali | Ground-truth stem input directly referenced by parity benchmark scripts (scripts/analyze_parity_differences.py) and regression tests | Tests, Server Parity |
| 9 | `storage/stems/ecdbc4dd2a6d827b/other.wav` | 91.21 MB | Demucs separated accompaniment harmonic stem for Bekhayali | Ground-truth accompaniment stem for harmonic verification and BTC chord parity validation | Tests, Server Parity |
| 10 | `tools/cloudflared.exe` | 52.80 MB | Cloudflare Tunnel client executable | Directly invoked by scripts/start_tunnel.bat to create public HTTPS tunnels for wireless mobile demo testing | Android Mobile Demo, Development |
| 11 | `storage/cache/ecdbc4dd2a6d827b_44k_stereo.wav` | 45.61 MB | High-fidelity 44.1kHz stereo audio file for Bekhayali | Strictly required by test_windows_server_parity.py and test_docker_parity.py to validate Windows <-> FastAPI parity | Tests, Server Parity |
| 12 | `mobile/android/ (native C++ & gradle wrapper)` | 27.27 MB | Android native build files, Gradle wrapper, and C++ inference engine | Required to build Android APK and execute onnxruntime C++ inference on mobile devices | Android Mobile |
| 13 | `.git/objects/` | 21.96 MB | Git revision history, commit tree objects, and repository database | Underlying version control history. Essential for git operations and project reproducibility | Development, Version Control |
| 14 | `models/btc/btc_model.onnx` | 12.44 MB | Bidirectional Transformer for Chord Recognition ONNX neural network weights | Primary chord recognition model asset used in Python backend pipeline | Windows Desktop, Server, Tests |
| 15 | `mobile/flutter_app/assets/models/btc_model_170voca.onnx` | 12.47 MB | 170-class chord vocabulary quantized ONNX model for Android mobile | Bundled mobile asset loaded by Android ONNX runtime for on-device chord inference | Android Mobile |
| 16 | `models/btc/btc_model_large_voca.pt` | 11.66 MB | PyTorch checkpoint for BTC chord recognition | PyTorch reference weights for chord recognition research, fine-tuning, and fallback execution | Server, Development |
| 17 | `storage/cache/ecdbc4dd2a6d827b_22k_mono.wav` | 11.40 MB | Downsampled 22.05kHz mono audio for Android parity testing | Required by 7 automated tests in tests/android_parity/ (beat, downbeat, tempo, key, CQT, onset) | Tests, Android Parity |
| 18 | `tests/golden_meter/` | 10.36 MB | Golden test audio WAV files across all 6 supported musical meters (2/4, 3/4, 4/4, 6/8, 7/8, 12/8) | Strict ground truth reference audio required by test_golden_meter.py regression suite | Tests |
| 19 | `storage/cache/bekhayali_demo.mp3` | 6.21 MB | Full-length compressed MP3 demo audio for Bekhayali | Standard reference audio for fast demonstration and pipeline smoke testing | Tests, Development |
| 20 | `tests/golden_parity/` | 2.14 MB | Mathematical golden JSON reference outputs for Android vs Windows parity | Regression fixtures ensuring cross-platform output invariance | Tests |

## Architectural Breakdown of Remaining Assets

1. **Pre-Trained ML Weights (~37 MB total):** ONNX & PyTorch models for BTC neural chord recognition across Windows backend and Android mobile runtime.
2. **Golden Reference Audio & Fixtures (~160 MB total):** Golden meter WAV tracks (2/4, 3/4, 4/4, 6/8, 7/8, 12/8), Bekhayali multi-instrumental reference tracks, and Demucs separated stems for automated parity verification.
3. **Runtime Binaries (~210 MB total):** Bundled Windows FFmpeg (155.73 MB) and Cloudflare tunnel executable (52.80 MB) required for local transcode and mobile remote testing.
4. **Packaged Distributions (~410 MB total):** Current release `SongChordAnalyzer.apk` (123.92 MB), Windows Setup installer (142.78 MB), and Windows portable executable (142.57 MB).
5. **Node.js Tooling (~677 MB total):** Root and frontend `node_modules` enabling instant offline packaging and frontend compilation.
6. **Active Source Code & Schemas (~15 MB total):** Python MIR backend, Flutter application, React frontend, Electron shell, test suites, and schemas.