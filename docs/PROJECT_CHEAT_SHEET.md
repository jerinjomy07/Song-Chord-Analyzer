# Song Chord Analyzer — Developer Quick Reference Cheat Sheet

---

## 1. Essential Commands

| Action | Command Line |
|---|---|
| **Start Backend Server** | `python run_app.py --no-browser` |
| **Start Remote Tunnel** | `scripts\start_tunnel.bat` |
| **Run Python Tests (44 tests)** | `python -m unittest discover -s tests -p "test_*.py"` |
| **Run Server Parity Test** | `python tests\server_parity\test_windows_server_parity.py` |
| **Run Flutter Tests (16 tests)** | `cd mobile\flutter_app && flutter test` |
| **Run Flutter Static Analysis** | `cd mobile\flutter_app && flutter analyze` |
| **Build Android Release APK** | `cd mobile\flutter_app && flutter build apk --release` |
| **Package Windows Desktop EXE** | `npm run dist` |

---

## 2. Ports & Network Endpoints

- **FastAPI Backend:** `http://0.0.0.0:8000` (Localhost: `http://127.0.0.1:8000`)
- **Health Diagnostic Probe:** `GET http://127.0.0.1:8000/api/health`
- **Audio Analysis Submission:** `POST http://127.0.0.1:8000/api/analyze`
- **Job Status Polling:** `GET http://127.0.0.1:8000/api/analyze/{id}`
- **Audio Stream (Seeking):** `GET http://127.0.0.1:8000/api/analysis/{id}/audio`
- **Cloudflare Tunnel URL:** `https://*.trycloudflare.com` (generated dynamically by `start_tunnel.bat`)

---

## 3. Key Storage Paths

- **Application Storage Root:** `%LOCALAPPDATA%\SongChordAnalyzer\`
- **Database File:** `%LOCALAPPDATA%\SongChordAnalyzer\database.sqlite`
- **Separated Stems Cache:** `%LOCALAPPDATA%\SongChordAnalyzer\stems\<hash>\`
- **Managed Song Library:** `%LOCALAPPDATA%\SongChordAnalyzer\library\<id>\`
- **Bundled FFmpeg:** `resources\ffmpeg\ffmpeg.exe`
- **Bundled Cloudflare Tunnel:** `tools\cloudflared.exe`
- **Production Android APK:** `SongChordAnalyzer.apk` (123.92 MB)
- **Production Windows Setup:** `dist_electron\SongChordAnalyzer-Setup.exe` (142.78 MB)
