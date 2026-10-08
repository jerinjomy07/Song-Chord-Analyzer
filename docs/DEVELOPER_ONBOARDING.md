# Developer Onboarding & Impact Analysis Guide

Welcome to Song Chord Analyzer! This guide gets you from a fresh repository clone to running, testing, and debugging the entire stack.

---

## 1. Toolchain & Environment Setup

### Required Runtimes
1. **Python 3.11 x64:** Used for the MIR backend. Recommended runtime: StemKit or standard Python 3.11 venv.
2. **Flutter SDK 3.24+:** Used for the Android mobile application (`flutter doctor`).
3. **Node.js 18+ & npm:** Used for the Electron desktop wrapper and Vite frontend.
4. **FFmpeg 6.0+:** Bundled at `resources/ffmpeg/ffmpeg.exe`.
5. **NVIDIA CUDA Toolkit 12.x (Optional):** For GPU-accelerated tensor inference.

### Quick Start Commands
```powershell
# 1. Start Python Backend
python run_app.py --no-browser

# 2. Run Python Backend Unit Tests
python -m unittest discover -s tests -p "test_*.py"

# 3. Start Flutter Mobile App (with connected device or emulator)
cd mobile/flutter_app
flutter pub get
flutter run

# 4. Start Windows Desktop App in Development Mode
npm install
npm run dev
```

---

## 2. "If I Change This..." Ripple-Effect Matrix

Before modifying any source file, consult this impact table to understand downstream dependencies:

| If You Change... | Direct Files Affected | Downstream Impact | Unaffected Components |
|---|---|---|---|
| **BTC Preprocessing / CQT** | `backend/preprocessing/cqt.py`, `backend/chord_recognition/btc_recognizer.py` | Changes chord posterior probabilities. Requires re-verifying golden parity tests (`tests/server_parity/`). | Mobile UI, Flutter app, SQLite schema, PDF layout. |
| **Ellis Beat Tracking or Meter Logic** | `backend/beats/`, `backend/meter/meter_detector.py` | Alters bar measure boundaries, tempo, and downbeat arrays. Requires running `tests/test_golden_meter.py`. | Mobile UI, React frontend, HTTP upload endpoints. |
| **`SongAnalysis` Schema (`song_analysis.schema.json`)** | `shared/music_schema/`, `backend/models/schemas.py`, `mobile/flutter_app/lib/models/song_analysis.dart` | **CRITICAL CONTRACT CHANGE.** Breaks database deserialization and mobile parsing unless updated across both Python and Dart simultaneously. | MIR algorithms, audio preprocessors. |
| **Flutter Mobile UI / Widgets** | `mobile/flutter_app/lib/screens/`, `lib/widgets/` | Changes visual appearance on mobile devices. | Host server, Python MIR engine, Windows desktop app. |
| **FastAPI REST Routes** | `backend/api/routes.py` | Modifies endpoint signatures. Requires updating `dev_http_analysis_engine.dart` and frontend API clients. | Internal MIR signal processing algorithms. |
| **PDF Layout / Fit-to-Page** | `mobile/flutter_app/lib/services/export_service.dart`, `backend/export/pdf_exporter.py` | Modifies printed document appearance. Requires running `tests/test_mobile_pdf_layout.py`. | Audio analysis, beat grids, playback synchronization. |
