# 🎵 SONG CHORD ANALYZER

[![Release](https://img.shields.io/badge/Release-v0.1.3-indigo.svg)](https://github.com/jerinjomy07/Song-Chord-Analyzer/releases/tag/v0.1.3)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011%20x64-blue.svg)](https://github.com/jerinjomy07/Song-Chord-Analyzer)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20Accelerated-orange.svg)](https://pytorch.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](docs/MODEL_LICENSING.md)

> **Standalone Windows Desktop Application for Automated Music Information Retrieval (MIR), Automatic Chord Recognition (ACR) & Persistent Song Library**

**Song Chord Analyzer** is a local-first Windows desktop application designed specifically for pianists, keyboardists, guitarists, worship teams, arrangers, and music producers. Drag and drop any music file (MP3, WAV, FLAC, M4A, AAC, OGG, WMA) or inspect a YouTube link, and the system automatically performs Demucs stem separation, BTC Transformer neural chord recognition, sub-bass inversion detection, beat/bar alignment, and musical section structuring to produce an interactive, musician-ready chord chart.

---

## 📥 Downloads & Windows Executables

Download the latest pre-built Windows standalone binaries from the **[v0.1.3 Release Page](https://github.com/jerinjomy07/Song-Chord-Analyzer/releases/tag/v0.1.3)**:

| Distribution Format | Description | Download Link |
| :--- | :--- | :--- |
| **Windows Installer** | Standard Windows setup with Start Menu & Desktop shortcuts | [📥 SongChordAnalyzer-Setup.exe](https://github.com/jerinjomy07/Song-Chord-Analyzer/releases/download/v0.1.3/SongChordAnalyzer-Setup.exe) |
| **Standalone Portable** | Single-file portable `.exe` requiring zero installation | [📥 SongChordAnalyzer.exe](https://github.com/jerinjomy07/Song-Chord-Analyzer/releases/download/v0.1.3/SongChordAnalyzer.exe) |
| **Pre-Extracted Directory** | Direct standalone folder | `dist_electron/win-unpacked/Song Chord Analyzer.exe` |

---

## 🌟 Key Features & What's New in v0.1.3

### 1. Persistent SQLite History & Song Library
- **Analyze Once, Keep Forever:** Every analyzed song is automatically saved to an isolated local SQLite database (`%LOCALAPPDATA%\SongChordAnalyzer\database.sqlite`).
- **Instant Historical Loading (<15ms):** Opening a song from History bypasses Demucs and neural model execution entirely. Audio and chord sheets load immediately.
- **Audio Library Management:** Audio is preserved in `%LOCALAPPDATA%\SongChordAnalyzer\library\<song-id>\`, ensuring charts, waveforms, and playback continue working even if you move or delete your original file.
- **Search & Sort:** Instant keyword search across song titles, filenames, and keys, with sorting by *Recently Opened*, *Recently Analyzed*, *Recently Modified*, and *Title (A–Z)*.
- **Favorites & Song Duplication:** Star your favorite arrangements or duplicate charts to keep alternate keys and revisions.

### 2. Full Song Title Renaming Freedom
- **On YouTube Inspection:** Edit and clean messy video titles (e.g. stripping artist tags, `| Official Video | 4K`) using the **Auto-Clean** button before starting.
- **In Upload Zone:** Edit the song title before analysis begins.
- **On Active Chord Sheet:** Click the **edit pencil** next to the song title in the header to rename the title inline anytime. All changes auto-save immediately to SQLite and update future PDF, TXT, and JSON exports.

### 3. Dedicated Automatic Chord Recognition (ACR) & Inversions
- **BTC Transformer Model:** Evaluates CQT spectral representations against a **170-chord vocabulary** (Major, Minor, 7th, Maj7, Min7, Dim, Aug, Sus4, Sus2, 6th, etc.).
- **Physical Bass-Stem Inversion Detection:** Isolates the Demucs bass stem and tracks sub-bass frequencies ($30\text{ Hz} - 350\text{ Hz}$) to identify true sounding bass notes (e.g. $F\sharp/A\sharp$, $A/C\sharp$, $D/F\sharp$, $E/G\sharp$, $C/E$, $G/B$).
- **Multi-Source Evidence Fusion:** Combines original mix BTC predictions, accompaniment stem predictions, physical bass tracking, and CQT Chroma profiles.

### 4. Interactive Musician Workflow
- **Auto-Scroll Playback:** Chord sheet automatically scrolls synchronously with audio playback, keeping active measures in view.
- **Interactive Chord Editor:** Click any chord to edit root, quality, bass note, or choose model-predicted alternative candidates.
- **Auto-Save Indicator:** Displays a debounced **"Saved ✓"** badge whenever chord edits, section renames, or transpositions are committed.
- **True Musical Transposer:** Shift the entire song ($+/- 11$ semitones) instantly while preserving chord quality, root spelling, and slash inversions.

### 5. Multi-Format Crash-Free Export
- **Printable PDF:** Clean, standard sheet music with boxed measures and section headers generated via ReportLab.
- **Monospace TXT:** Standard ASCII chart designed for stage binders and chord charts.
- **Structured JSON:** Machine-readable transcription format containing complete chord, beat, downbeat, and confidence metrics.

---

## 🛠️ System Architecture

```
song-chord-analyzer/
├── electron/
│   ├── main.cjs                 # Electron desktop lifecycle, port allocation & process tree management
│   ├── preload.cjs              # Secure contextBridge desktop IPC APIs
│   └── sign-noop.cjs            # Windows local build sign hook
├── backend/
│   ├── api/routes.py            # FastAPI REST endpoints (analysis, history, exports, stream)
│   ├── database/
│   │   ├── db.py                # Thread-safe SQLite connection factory with WAL mode & corruption recovery
│   │   └── repository.py        # SongRepository (instant load, duplicate detection, edits, ML feedback)
│   ├── audio/
│   │   ├── ffmpeg_utils.py      # Bundled FFmpeg audio conversion & metadata extraction
│   │   └── preprocessor.py      # Resampling, dynamics normalization, and cache management
│   ├── separation/
│   │   └── demucs_separator.py  # Demucs v4 GPU stem separation integration
│   ├── beat/beat_tracker.py     # Librosa dynamic programming BPM & beat onset tracker
│   ├── key/key_detector.py      # Multi-source K-S chromagram key estimation
│   ├── meter/meter_detector.py  # Beat periodicity meter estimator (4/4, 3/4, 2/4, 6/8)
│   ├── chord/
│   │   ├── btc.py               # Pretrained BTC Transformer recognizer
│   │   ├── bass.py              # Sub-bass pitch tracking & inversion analyzer
│   │   ├── chroma.py            # CQT-Chroma template matcher
│   │   ├── ensemble.py          # Multi-source evidence fusion engine
│   │   └── vocabulary.py        # 170-chord definitions, parsing, & enharmonics
│   ├── postprocessing/
│   │   ├── smoothing.py         # De-jittering and chord event consolidation
│   │   └── alignment.py         # Measure/bar container alignment
│   ├── sections/
│   │   └── section_detector.py  # Structural segmentation & repetition clustering
│   ├── transpose/
│   │   └── transpose_engine.py  # Transposition preserving qualities & inversions
│   ├── export/
│   │   ├── pdf_exporter.py      # Printable PDF chord sheet generator via ReportLab
│   │   ├── txt_exporter.py      # Monospace ASCII chord chart generator
│   │   └── json_exporter.py     # Structured transcription exporter
│   ├── config.py                # Storage paths (%LOCALAPPDATA%), FFmpeg, & CUDA configuration
│   ├── pipeline.py              # End-to-end master orchestrator & VRAM manager
│   └── main.py                  # FastAPI server & static SPA server
├── frontend/                    # Modern React 19 + Vite + Tailwind CSS interface
│   └── src/
│       ├── components/
│       │   ├── HistoryPage.tsx          # Song library, search, sort, and favorites
│       │   ├── RecentSongsSection.tsx   # Quick-access cards on Home screen
│       │   ├── DuplicateModal.tsx       # Content-hash duplicate audio modal
│       │   ├── YouTubeSourceZone.tsx    # Link inspection with Auto-Clean title
│       │   ├── UploadZone.tsx           # Audio drag-and-drop with pre-analysis rename
│       │   ├── SongHeader.tsx           # Title display with inline rename
│       │   ├── ChordSheet.tsx           # Synchronized auto-scroll chord sheet
│       │   ├── AudioPlayerTimeline.tsx  # Waveform scrubber & playback
│       │   ├── TransposerToolbar.tsx    # Semitone transposer
│       │   └── ExportToolbar.tsx        # PDF, TXT, JSON exporter
├── resources/ffmpeg/            # Bundled standalone FFmpeg binary
├── models/btc/                  # Pretrained BTC Transformer weights
├── dist_electron/               # Packaged Windows standalone executables & installer
├── run_app.py                   # Single-command Python launcher
└── run.bat                      # Windows one-click batch launcher
```

---

## 🚀 How to Run

### Method 1: Run the Standalone Windows App
Double-click `SongChordAnalyzer.exe` or run the installer `SongChordAnalyzer-Setup.exe`. No terminal or Python installation is required for end users.

### Method 2: Launch via Windows Batch Script
```cmd
run.bat
```

### Method 3: Developer Launch
```powershell
# 1. Install frontend dependencies and build
npm run build:frontend

# 2. Start Desktop Application
npm start
```

---

## 🧪 Testing & Verification

```powershell
# Run SQLite History & Library test suite
python tests/test_history_library.py

# Run chord vocabulary, parsing, inversion, and transposition tests
python tests/test_chord_vocabulary.py

# Run ground-truth accuracy evaluator
python tests/test_evaluator.py
```

---

## 📄 License & Model Provenance
See [`docs/MODEL_LICENSING.md`](docs/MODEL_LICENSING.md) for full licensing details:
- **Song Chord Analyzer Application:** MIT License
- **BTC Model:** MIT License (Park & Lee, ISMIR 2019)
- **Demucs Architecture:** MIT License (Meta AI Research)
- **FFmpeg:** LGPL v2.1+ / GPL v3.0 (Dynamic binary invocation)
