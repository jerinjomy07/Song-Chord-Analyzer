# Song Chord Analyzer — Complete Master Technical Guide (A–Z)

**Project Name:** Song Chord Analyzer  
**Current Production Version:** 1.0.0 (API: `1.0.0`, Schema: `1.0.0`, Android APK: `1.0.0+`, Windows App: `0.1.7`)  
**Package / Application IDs:**  
- Android Application ID: `com.songchordanalyzer.app`  
- Windows App ID: `com.songchordanalyzer.app` (Electron Product Name: `Song Chord Analyzer`)  
**Repository Branch:** `main` (Active Commit: `cab71a9`)  
**Supported Platforms:** Windows 10/11 x64 (Desktop Executable & Background MIR Engine), Android 8.0+ (Mobile Flutter App)  

---

## 1. Executive Summary

### What is Song Chord Analyzer?
Song Chord Analyzer is an automated Music Information Retrieval (MIR) and Automatic Chord Recognition (ACR) system designed to listen to any polyphonic music track (MP3, WAV, FLAC, M4A), isolate its harmonic stems, track its musical beat grid and downbeats across all metric time signatures (2/4, 3/4, 4/4, 6/8, 7/8, 12/8), recognize chord progressions with slash chord inversions using a deep Transformer neural network, and render an interactive, synchronized chord sheet and musician-grade one-page lead sheet PDF.

### What problem does it solve?
Transcribing songs by ear is tedious and difficult, especially for complex polyphonic mixes with dominant vocals, rapid bass modulations, and irregular time signatures (such as 7/8 or compound 6/8). Conventional chord recognizers produce chaotic frame-by-frame chord "blips", fail on inversions (e.g. C/E), confuse harmonic meter, and cannot format music into standard musician bar measures. Song Chord Analyzer solves this by combining neural stem separation (Demucs v4), deep Transformer chord posteriors (BTC 170-class vocabulary), sub-bass acoustic tracking, multi-hypothesis meter detection, and beat-synchronous simplicity regularization into an end-to-end, reproducible pipeline.

### How does it work?
1. The user selects an audio track in the Flutter Android app or Windows desktop app.
2. The audio is sent to the authoritative Python MIR analysis engine running on the host PC/laptop.
3. The engine performs stem separation, extracts multi-hypothesis tempo and Ellis beat grids, detects time signature and downbeats, infers chords on both the original mix and vocal-free accompaniment stem using the BTC Transformer, analyzes the isolated bass stem for acoustic bass fundamentals, and resolves slash chords.
4. The beat-synchronous chords are snapped to musical bar measures, structural sections (Intro, Verse, Chorus, Outro) are discovered via recurrence matrix clustering, and a structured `SongAnalysis` JSON object is generated.
5. The Flutter client or Electron frontend displays the interactive chord sheet with real-time playback tracking, instant transposition, and one-click export to a compact, single-page musician lead sheet PDF.

### What runs on Windows vs. Android vs. the Server?
- **On Windows:** The authoritative Python MIR engine, PyTorch neural networks (CUDA accelerated), Demucs stem separation, Librosa/SciPy signal processing, bundled FFmpeg decoder, FastAPI REST server, and optional Electron desktop shell.
- **On Android:** The cross-platform Flutter application providing the mobile UI, file selection, network transport (HTTP upload & polling), audio playback engine (`audioplayers`), transposition engine, local history caching (`sqflite`), and mobile vector PDF export (`pdf` package).
- **On the Server:** The FastAPI REST API mounts on port 8000, managing an asynchronous job queue (`ThreadPoolExecutor`) with admission control, hardware telemetry (`/api/health`), and managed library storage (`database.sqlite`).

### How does the phone connect?
The Android application provides three user-selectable connection modes:
1. **Local Network Mode (LAN / Wi-Fi):** The phone connects directly to the laptop's private Wi-Fi IP address (e.g. `http://192.168.0.180:8000`). Operates 100% offline without internet access.
2. **Remote Internet Mode (Cloudflare Tunnel):** The phone connects over public cellular data (4G/5G) or remote Wi-Fi to a secure Cloudflare Tunnel endpoint (`https://*.trycloudflare.com`). **The laptop still performs 100% of the computation.**
3. **Auto Connection Mode:** The app probes the Local LAN endpoint with a 1.5-second timeout; if reachable, it operates over LAN; if outside the home network, it automatically fails over to the Remote tunnel.

### Is it offline? Is it cloud-hosted?
- **Offline Status:** Once a song is analyzed, the song analysis, chord sheet, and playback audio are stored in local phone SQLite storage for **100% offline playback, transposition, and PDF export**. For *new* audio analysis, the mobile app requires a network connection to the laptop server (either local Wi-Fi or remote tunnel).
- **Cloud Hosting:** There is **no permanent cloud VM or third-party cloud compute**. The laptop acts as the dedicated personal compute server. The Cloudflare Tunnel provides transport encapsulation only.

---

## 2. Master Navigation & Documentation Index

This master document links directly to the 20 specialized technical blueprints across the repository:

1. [**System Architecture (`ARCHITECTURE.md`)**](ARCHITECTURE.md): End-to-end system topology, dual-client design, job queue admission control, single points of failure, and source quality map.
2. [**Music Analysis Engine Complete A–Z (`MUSIC_ANALYSIS_PIPELINE.md`)**](MUSIC_ANALYSIS_PIPELINE.md): Exhaustive 40-stage breakdown of MIR signal processing, Ellis beat tracking, multi-meter detection, Demucs stem separation, BTC Transformer inference, and slash chord tracking.
3. [**Android Mobile Architecture (`ANDROID_ARCHITECTURE.md`)**](ANDROID_ARCHITECTURE.md): Flutter widget hierarchy, responsive 2-column chord sheet grid, audio playback sync, transposition engine, and retired Kotlin native engine audit.
4. [**Windows Desktop Architecture (`WINDOWS_ARCHITECTURE.md`)**](WINDOWS_ARCHITECTURE.md): Electron wrapper, Vite/React frontend, background Python process management, NSIS installer, and portable executable.
5. [**FastAPI Server & API Reference (`API_REFERENCE.md`)**](API_REFERENCE.md): Complete REST endpoint documentation, header schemas, error responses, admission control, and job polling protocol.
6. [**Data Schema Contract (`DATA_SCHEMA.md`)**](DATA_SCHEMA.md): Exhaustive field-by-field reference for `SongAnalysis` JSON schema (v1.0.0) and Pydantic validators.
7. [**Dual-Mode Networking (`NETWORKING.md`)**](NETWORKING.md): Local LAN Wi-Fi configuration, Cloudflare Tunnel setup, firewall rules, latency diagnostics, and Auto failover state machine.
8. [**Build, Packaging & Release (`BUILD_AND_RELEASE.md`)**](BUILD_AND_RELEASE.md): Step-by-step instructions for building Android release APKs, Windows Electron installers, and Docker backend containers.
9. [**Testing, Verification & Parity (`TESTING_AND_PARITY.md`)**](TESTING_AND_PARITY.md): Verification test suites (44/44 Python tests, 16/16 Flutter tests), golden meter audio fixtures, and 100% Windows <-> FastAPI parity proofs.
10. [**Musician-Grade PDF & TXT Export (`PDF_EXPORT.md`)**](PDF_EXPORT.md): Adaptive measurement-based Fit-to-Page algorithm (ONE SONG = ONE A4 PAGE), typography hierarchy, and bar measure layouts.
11. [**Storage & Data Lifecycle (`STORAGE_AND_DATA_LIFECYCLE.md`)**](STORAGE_AND_DATA_LIFECYCLE.md): Audio upload lifecycle, hashing (`compute_audio_hash`), SQLite repository, stem retention, and cleanup rules.
12. [**Security Posture (`SECURITY.md`)**](SECURITY.md): Optional API key auth (`X-API-Key`), CORS policies, upload bounds, path traversal defenses, and firewall rules.
13. [**Troubleshooting & Runbooks (`TROUBLESHOOTING.md`)**](TROUBLESHOOTING.md): Diagnostic runbooks for phone connection drops, tunnel restarts, CUDA OOM, and audio decode failures.
14. [**Live Demonstration Guide (`DEMO_GUIDE.md`)**](DEMO_GUIDE.md): Scripted walkthrough for demonstrating Local LAN and Remote 4G/5G mobile analysis.
15. [**Developer Onboarding & Impact Map (`DEVELOPER_ONBOARDING.md`)**](DEVELOPER_ONBOARDING.md): Toolchain setup, local run commands, and the "If I Change This..." dependency ripple-effect matrix.
16. [**Known Limitations & Boundaries (`KNOWN_LIMITATIONS.md`)**](KNOWN_LIMITATIONS.md): Transparent disclosure of hardware requirements, model constraints, and deployment scope.
17. [**Future Architectural Roadmap (`FUTURE_ROADMAP.md`)**](FUTURE_ROADMAP.md): Evolutionary roadmap covering Cloud VM migration, mobile neural runtime, and macOS/Linux builds.
18. [**Technical Glossary (`GLOSSARY.md`)**](GLOSSARY.md): Beginner-friendly analogies paired with formal scientific definitions for all MIR and engineering concepts.
19. [**Project Source File Index (`PROJECT_FILE_INDEX.md`)**](PROJECT_FILE_INDEX.md): File-by-file catalog of every active source file with classification, criticality, and dependencies.
20. [**One-Page Developer Cheat Sheet (`PROJECT_CHEAT_SHEET.md`)**](PROJECT_CHEAT_SHEET.md): High-density reference for commands, paths, ports, and troubleshooting steps.

---

## 3. Project Identity & Metadata

| Attribute | Specification | Source in Repository |
|---|---|---|
| **Product Name** | Song Chord Analyzer | `package.json`, `pubspec.yaml`, `electron-builder.yml` |
| **Current Version** | `1.0.0` (Backend / Schema / Mobile) / `0.1.7` (Electron Shell) | `backend/config.py`, `package.json`, `pubspec.yaml` |
| **Android Application ID** | `com.songchordanalyzer.app` | `mobile/flutter_app/android/app/build.gradle` |
| **Windows Application ID** | `com.songchordanalyzer.app` | `electron-builder.yml` |
| **Windows App Title** | Song Chord Analyzer | `electron/main.cjs` |
| **Repository Branch** | `main` | Git repository HEAD |
| **Active Git Commit** | `cab71a9` | Git repository commit log |
| **Data Contract Schema** | `SongAnalysis` v1.0.0 (Draft 2020-12) | `shared/music_schema/song_analysis.schema.json` |
| **Backend REST API** | FastAPI 1.0.0 | `backend/main.py` |
| **ML Chord Model** | BTC (Bidirectional Transformer for Chords) | `models/btc/btc_model.onnx`, `btc_model_large_voca.pt` |
| **Stem Separation Model**| Demucs v4 (`htdemucs` 4-stem PyTorch) | PyTorch Hub / TorchAudio / StemKit runtime |
| **Host Operating System** | Windows 10/11 x64 (Primary development & compute host) | Tested on NVIDIA GeForce RTX 3050 Laptop GPU |
| **Mobile Operating System**| Android 8.0+ (API 26+) | `minSdkVersion 24`, `targetSdkVersion 34` |

---

## 4. Chronological Project Evolution

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                       PROJECT EVOLUTION PHASES                                       │
├─────────────────┬─────────────────┬─────────────────┬─────────────────┬──────────────────────────────┤
│ PHASE 0 & 1     │ PHASE 2         │ PHASE 3         │ PHASE 4         │ PHASE 5 & 6                  │
│ Concept &       │ On-Device       │ Parity Crisis & │ Server-Backed   │ Dual-Network Demo &          │
│ Windows Engine  │ Kotlin Attempt  │ Engine Remediation│ Android Architecture│ Responsive Musician Sheet│
│ (Sept 2026)     │ (Late Sept 2026)│ (Early Oct 2026)│ (Oct 2026)      │ (Oct 2026 - Present)         │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┴──────────────────────────────┘
```

### Phase 0: Conceptual Foundation (September 2026)
- **Goal:** Create an automated music chord recognition and lead-sheet generator for musicians.
- **Initial Tech Choice:** Python MIR toolchain (Librosa, SciPy, PyTorch).
- **Core Architecture:** Acoustic feature extraction (CQT, Chroma) combined with deep neural chord recognition.

### Phase 1: Windows Desktop Analyzer (September 2026)
- **Implementation:** Built `SongAnalyzerPipeline` utilizing the pre-trained BTC Transformer model, Krumhansl-Schmuckler key detector, and Ellis beat tracker.
- **Packaging:** Wrapped in an Electron desktop application (`electron/main.cjs`) with a React/Vite UI (`frontend/src/`) and compiled into NSIS installers using `electron-builder`.
- **Finding:** Achieved accurate chord recognition on isolated audio files, but standard mixes suffered vocal interference and lack of inversion accuracy. Added Demucs stem separation and sub-bass fundamental analysis.

### Phase 2: On-Device Android Kotlin Attempt (Late September 2026)
- **Goal:** Provide a standalone Android application that analyzes songs directly on mobile devices without needing a computer.
- **Implementation:** Created custom Kotlin MIR algorithms in `mobile/flutter_app/android/app/src/main/kotlin/`: `AudioDecoder.kt`, `CqtExtractor.kt`, `EllisBeatTracker.kt`, `KeyDetector.kt`, `TempoAndMeterDetector.kt`, and exported a quantized 170-class BTC model (`btc_model_170voca.onnx`) run via `onnxruntime-android`.
- **Critical Problems Encountered:**
  1. *Mobile Memory Limitations:* Demucs stem separation requires > 2 GB of RAM; mobile devices could not run Demucs stems locally without crashing (OOM).
  2. *Signal Processing Discrepancies:* The Kotlin CQT extractor and FFT implementation diverged from Librosa's CQT filterbank, resulting in degraded chord accuracy.
  3. *Tritone Pitch Class Scrambling:* A bug in `KeyDetector.kt` (`chroma[b % 12] += mag` on a 24-bin/octave CQT) mapped bin 0 (C) and bin 12 (F#) to the same pitch class, scrambling key detection.
  4. *Meter & Tempo Failure:* As documented in `docs/METER_TEMPO_FAILURE_REPORT.md`, triple-meter songs like *Bekhayali* (3/4 at 86.1 BPM) were misidentified as 4/4 at 117.5 BPM.

### Phase 3: Engine Remediation & Validation (Early October 2026)
- **Directive:** Fix the Windows reference engine first; do not force mobile to reproduce flawed heuristics.
- **Fixes Applied:**
  - Implemented multi-hypothesis tempo estimation testing octave candidates (0.5x, 1.0x, 2.0x).
  - Built comprehensive metric bar evaluators for all six time signatures: 2/4, 3/4, 4/4, 6/8, 7/8 (with additive subgroupings 2+2+3, 2+3+2, 3+2+2), and 12/8.
  - Achieved 10/10 perfect detection on golden meter audio fixtures (`tests/golden_meter/`).
  - Added XML escaping to ReportLab PDF generation to prevent crash on special characters (`<`, `>`, `&`).
  - Audited YouTube extraction contract to require audio inputs.

### Phase 4: Server-Backed Mobile Architecture (October 2026)
- **Architectural Shift:** Shifted Android strategy from faulty on-device processing to **Server-Backed Architecture**.
- **Design:** The phone acts as a clean, responsive client interface. The laptop runs a background FastAPI server exposing the authoritative Python MIR pipeline.
- **Result:** Phone users obtain the full power of CUDA-accelerated Demucs stem separation, exact BTC Transformer inference, and perfect meter detection.
- **Verification:** Verified 21/21 parity checks between the Windows engine and FastAPI server on *Bekhayali* with 0.000000s timing delta (`WINDOWS_SERVER_PARITY_REPORT.md`).

### Phase 5: Dual-Mode Networking (October 2026)
- **Goal:** Allow the phone to connect both inside the house and on the go without paying for cloud servers.
- **Implementation:** Implemented `ServerConfigService` supporting:
  - Local LAN mode (`http://192.168.x.x:8000`) for zero-internet home Wi-Fi.
  - Remote Internet mode (`https://*.trycloudflare.com`) via Cloudflare Tunnel for cellular 4G/5G data.
  - Auto Connection mode with automatic local probe and remote failover.

### Phase 6: Responsive Musician Sheet & Fit-to-Page PDF (Current Final State)
- **UI Redesign:** Replaced full-width horizontal bar cards with a responsive **2-column chord sheet grid**, doubling chord density on portrait mobile displays.
- **PDF Redesign:** Replaced the mobile UI screenshot export with an adaptive, musician-grade lead sheet (`| Dm | Asus4 | D |`).
- **Fit-to-Page Algorithm:** Implemented adaptive measurement scaling to guarantee **ONE SONG = ONE A4 PAGE** across both Android and Windows PDF exporters.
- **Project Sanitization:** Audited repository size, safely removing 4.51 GB of regenerable build intermediates and caches while protecting all models, tests, and active binaries.

---

## 5. Technology Stack Summary

| Technology | Role | Language | Source Location | Version | Criticality | Verification Status |
|---|---|---|---|---|---|---|
| **Python** | MIR backend & analysis engine | Python | `backend/` | 3.11 / 3.14 compatible | Critical | ✓ Verified (44/44 tests passing) |
| **FastAPI** | REST API & job coordinator | Python | `backend/main.py`, `backend/api/` | 0.115+ | Critical | ✓ Verified (100% server parity) |
| **PyTorch** | Neural network tensor runtime | Python / C++ | PyTorch runtime | 2.5.0+cu124 | Critical | ✓ Verified (CUDA acceleration active) |
| **Demucs v4** | 4-stem audio source separation | Python / PyTorch | `backend/separation/` | `htdemucs` v4 | Critical | ✓ Verified (Stems cached & produced) |
| **BTC Transformer**| 170-class chord recognition | Python / ONNX | `models/btc/`, `backend/chord_recognition/` | Large voca | Critical | ✓ Verified (100% chord match) |
| **Librosa** | Signal processing & CQT | Python | `backend/preprocessing/`, `backend/beats/` | 0.10.2+ | Critical | ✓ Verified |
| **SciPy / NumPy** | FFT, spectral flux & filters | Python / C | Core libraries | SciPy 1.14+, NumPy 2.1+ | Critical | ✓ Verified |
| **ReportLab** | Windows/Server PDF lead sheet generator | Python | `backend/export/pdf_exporter.py` | 4.2+ | Critical | ✓ Verified (1-page adaptive fit) |
| **Flutter** | Cross-platform mobile UI | Dart | `mobile/flutter_app/lib/` | Flutter 3.24+ (Dart 3.5+) | Critical | ✓ Verified (16/16 tests passing) |
| **Audioplayers** | Mobile audio playback engine | Dart / Android | `mobile/flutter_app/` | 6.0+ | Critical | ✓ Verified on device |
| **Dart PDF** | Mobile vector PDF export | Dart | `mobile/flutter_app/lib/services/export_service.dart` | `pdf` 3.11+ | Critical | ✓ Verified (1-page adaptive fit) |
| **SQLite / Sqflite**| Mobile & server history storage| SQL / C | `backend/models/database.py`, `history_service.dart` | SQLite 3 | Critical | ✓ Verified |
| **Electron** | Windows desktop window shell | JS / C++ | `electron/main.cjs` | 33.2.1 | Optional | ✓ Verified (`npm run dist` passes) |
| **Vite & React** | Windows desktop web UI | TypeScript | `frontend/` | Vite 5.4+, React 18 | Optional | ✓ Verified |
| **FFmpeg** | Audio decoding & resampling | C / CLI | `resources/ffmpeg/ffmpeg.exe` | 6.0+ static | Critical | ✓ Verified (Used by backend config) |
| **Cloudflare Tunnel**| Remote HTTPS tunnel transport| Go / CLI | `tools/cloudflared.exe` | 2024.x | Optional | ✓ Verified (`scripts/start_tunnel.bat`) |
| **Kotlin (Retired)**| Historical on-device analysis | Kotlin | `mobile/.../android/app/src/main/kotlin/` | Kotlin 1.9+ | Legacy | 🗑 Legacy / Retired (Server-backed used) |

---

## 6. Language Distribution & Architectural Boundaries

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             LANGUAGE BOUNDARY MAP                                │
├──────────────────────────────────────┬───────────────────────────────────────────┤
│ BACKEND & COMPUTE (Python)           │ FRONTEND MOBILE (Dart / Flutter)          │
│ • Audio decoding & Demucs separation │ • Mobile UI screens & widgets             │
│ • Ellis beat & downbeat tracking     │ • Audio playback synchronization          │
│ • BTC Transformer chord recognition  │ • Transposition & semitone shift logic    │
│ • Slash chord & inversion analysis   │ • Local SQLite history persistence        │
│ • FastAPI HTTP server & job queue    │ • Client-side vector PDF generation       │
├──────────────────────────────────────┼───────────────────────────────────────────┤
│ DESKTOP SHELL (JavaScript / TS)      │ RETIRED ON-DEVICE (Kotlin)                │
│ • Electron window management         │ • Historical on-device MIR attempt        │
│ • Python process spawning & kill     │ • Retired due to Demucs RAM & CQT bugs    │
│ • React / Vite desktop interface     │ • Preserved in repo for research only     │
└──────────────────────────────────────┴───────────────────────────────────────────┘
```

1. **Python (Backend & Analysis Core):**
   - *Starts:* When audio bytes are received via HTTP upload or file selection.
   - *Ends:* When the validated `SongAnalysis` data structure is assembled and returned as JSON.
   - *Scope:* Audio preprocessing, Demucs stem separation, Ellis beat tracking, K-S key detection, BTC Transformer inference, sub-bass register tracking, and server PDF export.
2. **Dart / Flutter (Cross-Platform Mobile Application):**
   - *Starts:* Application boot on Android device (`main.dart`).
   - *Ends:* User interactions, screen navigation, network calls, audio playback, and client-side vector PDF generation.
   - *Scope:* UI rendering, state management, HTTP communication with the server, audio playback sync, local transposition, and offline history storage.
3. **JavaScript / TypeScript (Windows Desktop Wrapper & Web UI):**
   - *Starts:* Launch of the Windows desktop application (`electron/main.cjs`).
   - *Ends:* Spawning the background Python engine (`run_app.py`), managing the window lifecycle, and rendering the React frontend (`frontend/src/`).
4. **Kotlin (Android Native - Legacy / Research Component):**
   - *Scope:* The historical attempt at local on-device MIR in `mobile/.../android/app/src/main/kotlin/`. Now superseded by the authoritative FastAPI server architecture.

---

## 7. Status Matrix of Features

| Feature | Windows Desktop | Android Mobile | Backend Server | Offline Capability | Verification Status | Architectural Notes |
|---|:---:|:---:|:---:|:---:|:---:|---|
| **Audio File Upload** | ✓ | ✓ | ✓ | Network req. for new | **✓ Verified** | Supports MP3, WAV, FLAC, M4A up to 100 MB. |
| **Demucs Stem Separation** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | Requires CUDA / Host RAM; runs on laptop server. |
| **Ellis Beat Tracking** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | Standard Ellis dynamic programming beat tracker. |
| **Multi-Meter Detection** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | 2/4, 3/4, 4/4, 6/8, 7/8, 12/8 verified on golden audio. |
| **BTC Chord Recognition** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | 170-class vocabulary Transformer model. |
| **Slash Chord Inversions** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | Sub-bass fundamental tracking on isolated bass stem. |
| **Section Segmentation** | ✓ | N/A (Server) | ✓ | Host only | **✓ Verified** | Recurrence matrix clustering with neutral labels. |
| **Interactive Chord Grid** | ✓ | ✓ | N/A | **100% Offline** | **✓ Verified** | Mobile uses high-density 2-column responsive layout. |
| **Synchronized Playback** | ✓ | ✓ | ✓ (Audio stream) | **100% Offline** | **✓ Verified** | Auto-scrolls and highlights active bar and chord. |
| **Real-Time Transposition** | ✓ | ✓ | ✓ (API endpoint)| **100% Offline** | **✓ Verified** | -11 to +11 semitones with enharmonic spelling. |
| **Musician-Grade PDF** | ✓ | ✓ | ✓ | **100% Offline** | **✓ Verified** | Adaptive fit scales document to **ONE A4 PAGE**. |
| **Local History Storage** | ✓ | ✓ | ✓ | **100% Offline** | **✓ Verified** | Mobile uses `sqflite`; server uses `database.sqlite`. |
| **Local LAN Mode** | N/A | ✓ | ✓ | **100% Offline** | **✓ Verified** | Works without internet over local router/hotspot. |
| **Remote Tunnel Mode** | N/A | ✓ | ✓ | Internet req. | **✓ Verified** | Uses Cloudflare Tunnel (`cloudflared`) to laptop. |
| **Auto Connection Mode** | N/A | ✓ | ✓ | Hybrid | **✓ Verified** | 1.5s LAN probe with automatic remote failover. |
| **YouTube Extraction** | ⚠ | ⚠ | ⚠ | Internet req. | **⚠ Partially Impl.** | Metadata lookup works; analysis contract requires local file. |

---

## 8. "Song Chord Analyzer Explained For Me" (Beginner-Friendly Walkthrough)

*Imagine you are a guitarist or pianist who wants to learn a song, but you cannot find accurate chord charts online, or the song is in an unusual time signature like 7/8.*

### What happens step-by-step when you press "Analyze Song"?

```
[1. Select Audio] ──► [2. Upload] ──► [3. Stem Split] ──► [4. Beat & Meter] ──► [5. Neural Chords] ──► [6. Bass Inversion] ──► [7. Chord Sheet & PDF]
  Phone selects         Phone sends     Laptop separates    Laptop finds beats    AI listens to guitar  Laptop finds lowest    Phone displays 2-col
  audio file            to laptop       vocals & bass       & time signature      & piano chords        bass note (e.g. C/E)   sheet & 1-page PDF
```

1. **You Pick the Song:** You open the app on your Android phone and pick an MP3 file from your music collection.
2. **The Song Goes to Your Laptop:** Because deep-learning music analysis requires heavy processing and a GPU, your phone sends the audio file to your laptop over your home Wi-Fi (or over the cellular tunnel if you are away).
3. **The Laptop Separates the Instruments:** Your laptop uses an AI called **Demucs**. Demucs acts like a musical prism: it splits the song into separate audio tracks for Bass, Drums, Vocals, and Other Instruments. This ensures singers do not confuse the chord recognizer!
4. **The Laptop Finds the Beat and Time Signature:** The engine taps along with the song to calculate the BPM (tempo) and determines whether the song is in 4/4 (standard pop), 3/4 (waltz), or 7/8 (complex progressive rock/folk).
5. **The AI Listens to the Harmony:** The engine passes the clean instruments into a deep neural network called **BTC** (Bidirectional Transformer for Chords). BTC listens to the musical notes and outputs chord probabilities (e.g., 90% D Minor, 8% F Major).
6. **The Engine Checks the Bass Note:** The engine checks the isolated bass guitar track. If the chord is C Major but the bass player is playing E, the engine outputs **C/E** (a slash chord inversion).
7. **The Sheet Appears on Your Phone:** The laptop formats the chords into clean bars, measures, and sections (Intro, Verse, Chorus) and sends the completed data back to your phone.
8. **You Play Along:** Your phone displays a clean 2-column grid. As the song plays, the current chord lights up in real time, and the screen auto-scrolls. If you need to print it, tapping "Export PDF" generates a single-page musician lead sheet!

---

## 9. Claims We Should Not Make (Fact-Checked Transparency)

To maintain absolute scientific and technical integrity, the following claims **must never be made**:

1. **"Android performs full on-device AI analysis locally without a computer":** **FALSE.** Full MIR analysis requires Demucs stem separation and the full BTC Transformer, which run on the host PC/laptop. The Android app is a server-backed client.
2. **"The application is completely offline for NEW song analyses":** **FALSE.** Once a song is analyzed, it can be opened, played, transposed, and exported 100% offline from local storage. However, analyzing a *new* audio file requires a connection to the laptop server.
3. **"Remote Internet Mode runs on a free cloud supercomputer":** **FALSE.** The Cloudflare Tunnel merely acts as an encrypted internet cable. Your physical laptop at home is doing 100% of the actual computation. If your laptop is powered off or in sleep mode, Remote analysis will not work.
4. **"YouTube songs can be downloaded directly inside the mobile analysis pipeline":** **FALSE.** The current production contract requires user-supplied local audio files. While YouTube metadata lookup exists, direct streaming extraction is not part of the active production pipeline.
5. **"Passing the golden test track means all songs are 100% accurate":** **FALSE.** *Bekhayali* was used as an authoritative golden benchmark for mathematical cross-platform parity (matching beats, downbeats, key, and chords). Real-world accuracy on other songs depends on audio mix quality, tuning, and arrangement complexity.
