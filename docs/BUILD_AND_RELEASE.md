# Build, Packaging & Release Engineering

This document details the exact commands, toolchains, and packaging pipelines used to build production artifacts for Windows desktop, Android mobile, and containerized server environments.

---

## 1. Android Mobile APK Build

### 1.1 Prerequisites
- Flutter SDK 3.24+ (`C:\Users\jerin\flutter\bin\flutter.bat`).
- Android SDK (API 34 / Java 17).
- Pre-trained quantized ONNX model in assets: `mobile/flutter_app/assets/models/btc_model_170voca.onnx`.

### 1.2 Build Commands
From repository root:
```powershell
cd mobile/flutter_app

# 1. Clean build directory & fetch packages
flutter clean
flutter pub get

# 2. Run static analysis & test suite
flutter analyze
flutter test

# 3. Build optimized release APK
flutter build apk --release

# 4. Build release APK with hardcoded default remote URL (Optional)
flutter build apk --release --dart-define=API_BASE_URL=https://your-tunnel.trycloudflare.com
```

### 1.3 Artifact Output
- **Raw Gradle Output:** `mobile/flutter_app/build/app/outputs/flutter-apk/app-release.apk`
- **Root Release Copy:** `SongChordAnalyzer.apk` (123.92 MB).
- **Contents:** Stripped Flutter AOT runtime, JNI shared libraries (`libapp.so`, `libflutter.so`, `libonnxruntime.so`), bundled assets, fonts, and icons.

---

## 2. Windows Desktop Executable Build

### 2.1 Prerequisites
- Node.js 18+ and npm (`package.json`).
- Python 3.11 with virtual environment containing PyTorch, Librosa, and Demucs.
- Application icon at `build/app.ico`.

### 2.2 Build Commands
From repository root:
```powershell
# 1. Install desktop & frontend dependencies
npm install
npm run frontend:install

# 2. Compile React frontend into static bundle (frontend/dist/)
npm run build:frontend

# 3. Package Windows desktop application via electron-builder
npm run dist
```

### 2.3 Packaging Specification (`electron-builder.yml`)
- **Target Formats:**
  1. `nsis` (x64 Windows Setup Installer) -> `dist_electron/SongChordAnalyzer-Setup.exe` (142.78 MB).
  2. `portable` (x64 Standalone Executable) -> `dist_electron/SongChordAnalyzer.exe` (142.57 MB).
- **Bundled Resources:** Automatically packages `resources/ffmpeg/ffmpeg.exe`, `models/btc/`, and unpacked backend source files.
- **Signing:** Uses `electron/sign-noop.cjs` for unsigned local development builds.

---

## 3. Backend Docker Container Build

### 3.1 Dockerfile Overview (`Dockerfile`)
- Base image: `python:3.11-slim` with system FFmpeg, libsndfile1, and git installed.
- Exposes port `8000`.
- Health check: Probes `http://localhost:8000/api/health` every 30 seconds.

### 3.2 Build & Run Commands
```powershell
# 1. Build Docker image
docker build -t song-chord-analyzer-backend .

# 2. Run container with GPU acceleration
docker run -d --gpus all -p 8000:8000 -v song_data:/app/storage --name song-analyzer song-chord-analyzer-backend

# 3. Run container in CPU mode
docker run -d -p 8000:8000 -v song_data:/app/storage --name song-analyzer song-chord-analyzer-backend
```
