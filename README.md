# 🎵 SONG CHORD ANALYZER

> **Standalone Windows Desktop Application for Automated Music Information Retrieval (MIR) & Automatic Chord Recognition (ACR)**

**Song Chord Analyzer** is a local-first Windows desktop application designed specifically for pianists, keyboardists, guitarists, worship teams, arrangers, and producers. Drag and drop any music file (MP3, WAV, FLAC, M4A, AAC, OGG, WMA) onto the application window, and the system automatically performs stem separation, neural chord recognition, sounding bass inversion detection, beat/bar alignment, and musical section structuring to produce an interactive, musician-ready chord chart.

---

## 🌟 Key Highlights

### 1. 100% Automated Multi-Stage Local Pipeline
- **Zero Terminal Commands:** Musician-friendly interface. No manual stem exports, model toggles, or Python terminal setups.
- **Local-First Privacy:** Audio is processed entirely on the local machine with hardware acceleration.
- **Standalone Windows Distribution:** Packaged as both an installer (`SongChordAnalyzer-Setup.exe`) and portable executable (`SongChordAnalyzer.exe`).

### 2. Dedicated Automatic Chord Recognition (ACR)
- **Dedicated Neural Model:** Employs the **BTC (Bidirectional Transformer for Chord Recognition)** model trained on CQT representations with a **170-chord vocabulary** (Major, Minor, 7th, Maj7, Min7, Dim, Aug, Sus4, Sus2, 6th, etc.).
- **Authentic Confidence Scores:** Reports genuine model probabilities (never fabricated) and surfaces alternative candidate chords when harmonic ambiguity occurs.

### 3. Explicit Bass-Stem Inversion & Slash Chord Detection
- Seamlessly isolates the bass stem via local Demucs v4.
- Analyzes sub-bass frequencies ($30\text{ Hz} - 350\text{ Hz}$) on the isolated bass line to detect the true sounding bass note.
- Accurately distinguishes root chords from inversions and slash chords (e.g. $F\sharp/A\sharp$, $A/C\sharp$, $D/F\sharp$, $E/G\sharp$, $C/E$, $G/B$).

### 4. Multi-Source Harmonic Ensemble Fusion
- Fuses evidence across four harmonic channels:
  1. Original Mix BTC prediction
  2. Accompaniment Stem BTC prediction (vocals removed)
  3. Physical Bass Stem pitch tracking
  4. Harmonic Pitch Class Profile (HPCP / CQT Chroma) templates

### 5. Musical Beat & Bar Alignment
- Detects song tempo (**BPM**), beat onsets, downbeats, and estimates **time signatures** ($4/4, 3/4, 2/4, 6/8$).
- Aligns chord transitions to musical bars and beats rather than arbitrary decimal seconds.
- De-jitters transient classification glitches while preserving fast half-bar musical transitions.

### 6. Section Detection & Repetition Recognition
- Segments and clusters musical sections: `INTRO`, `VERSE 1`, `CHORUS`, `VERSE 2`, `BRIDGE`, `OUTRO`.
- Identifies repeated harmonic progressions across the arrangement.
- Allows user renaming of any section with instant updates across the chord sheet.

### 7. Interactive Musician UI & Audio Player
- **Interactive Timeline Scrubber:** Audio playback synchronized with active chord markers and section blocks.
- **Interactive Chord Sheet:** Click any chord to edit root, quality, bass note, or choose from model-predicted alternatives.
- **Musically Correct Transposer:** Transpose the whole song ($+/- 11$ semitones) instantly while preserving chord quality, root, and slash bass (e.g. $A/C\sharp + 2 = B/D\sharp$).

### 8. Multi-Format Export
- **Printable PDF:** Clean, professional sheet music generated via ReportLab with boxed measures and section headers.
- **Monospace TXT:** Standard ASCII text chord chart for easy copy-pasting.
- **Structured JSON:** Machine-readable transcription format containing complete chord, beat, timing, and confidence data.

### 9. NVIDIA RTX 3050 Hardware Acceleration & VRAM Management
- Auto-detects NVIDIA GPUs on startup and enables CUDA acceleration.
- Sequential memory management (`torch.cuda.empty_cache()` between separation and chord recognition) guarantees execution within 4GB - 6GB VRAM envelopes.
- Automatic graceful fallback to CPU if no compatible GPU is present.

---

## 🛠️ System Architecture

```
song-chord-analyzer/
├── electron/
│   ├── main.cjs                 # Electron main process (lifecycle, dynamic port, process management)
│   ├── preload.cjs              # Safe contextBridge desktop APIs
│   └── sign-noop.cjs            # Windows local build sign hook
├── backend/
│   ├── api/routes.py            # FastAPI REST endpoints & background tasks
│   ├── audio/
│   │   ├── ffmpeg_utils.py      # Bundled FFmpeg converter & metadata extractor
│   │   └── preprocessor.py      # Resampling, dynamics normalization, cache manager
│   ├── separation/
│   │   └── demucs_separator.py  # StemKit / Demucs v4 GPU integration
│   ├── beat/beat_tracker.py     # Librosa dynamic programming BPM & beat tracker
│   ├── key/key_detector.py      # Multi-source K-S chromagram key estimation
│   ├── meter/meter_detector.py  # Beat periodicity meter estimator (4/4, 3/4, 2/4, 6/8)
│   ├── chord/
│   │   ├── base.py              # ChordRecognizer abstract base interface
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
│   │   ├── pdf_exporter.py      # Printable PDF generator via ReportLab
│   │   ├── txt_exporter.py      # Monospace ASCII chord chart generator
│   │   └── json_exporter.py     # Structured transcription exporter
│   ├── evaluation/
│   │   └── evaluator.py         # Ground-truth accuracy benchmarking suite
│   ├── config.py                # Dynamic Windows paths (%LOCALAPPDATA%), FFmpeg, & CUDA config
│   ├── pipeline.py              # End-to-end master orchestrator & VRAM manager
│   └── main.py                  # FastAPI application entrypoint & static SPA server
├── frontend/                    # Modern React 19 + Vite + Tailwind CSS interface
├── resources/ffmpeg/            # Bundled standalone FFmpeg binary
├── models/btc/                  # Pretrained BTC Transformer weights (170-chord vocabulary)
├── dist_electron/               # Packaged Windows executables & NSIS installer
├── electron-builder.yml         # Windows installer & packaging configuration
├── docs/MODEL_LICENSING.md      # Comprehensive model licensing documentation
├── run_app.py                   # Single-command launcher
└── run.bat                      # Windows one-click batch launcher
```

---

## 🚀 Running the Application

### 1. Launch as Desktop Application (Electron)
```powershell
# Start Electron desktop shell with integrated Python backend
npm start
```

### 2. Standalone Windows Executables
Built binaries are located in `dist_electron/`:
- **Installer:** `dist_electron/SongChordAnalyzer-Setup.exe` (NSIS installer with desktop & start menu shortcuts)
- **Portable:** `dist_electron/SongChordAnalyzer.exe` (Standalone portable executable)
- **Unpacked:** `dist_electron/win-unpacked/Song Chord Analyzer.exe`

### 3. One-Click Batch Launcher
Double-click `run.bat` or run:
```powershell
.\run.bat
```

---

## 🧪 Testing & Verification

```powershell
# Run chord vocabulary, parsing, inversion, and transposition tests
python tests/test_chord_vocabulary.py

# Run ground-truth accuracy evaluator
python tests/test_evaluator.py

# Run end-to-end audio analysis pipeline on real audio file
python test_pipeline_run.py
```

---

## 📄 License & Model Provenance
See [`docs/MODEL_LICENSING.md`](docs/MODEL_LICENSING.md) for full licensing information:
- **Song Chord Analyzer Application:** MIT License
- **BTC Model:** MIT License (Park & Lee, ISMIR 2019)
- **Demucs Architecture:** MIT License (Meta AI Research)
- **FFmpeg:** LGPL v2.1+ / GPL v3.0 (Dynamic binary invocation)
- **Librosa / SciPy / NumPy / PyTorch:** Permissive open source licenses (ISC / BSD)
