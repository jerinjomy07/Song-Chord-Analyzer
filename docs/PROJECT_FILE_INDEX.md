# Complete Project File Index & Source Map

This index catalogs every important source, configuration, and asset file in Song Chord Analyzer.

---

| File Path | Primary Role | Language | Criticality | Dependencies |
|---|---|:---:|:---:|---|
| [`backend/main.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/main.py) | FastAPI app entrypoint, CORS, auth, health check | Python | **Critical** | `fastapi`, `uvicorn`, `torch` |
| [`backend/config.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/config.py) | Path resolution, hardware probing, storage paths | Python | **Critical** | `pathlib`, `torch` |
| [`backend/pipeline.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/pipeline.py) | Central 12-stage MIR orchestrator & VRAM manager | Python | **Critical** | `Demucs`, `BTC`, `Librosa` |
| [`backend/api/routes.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/api/routes.py) | REST API endpoints, job queue, upload handler | Python | **Critical** | `fastapi`, `sqlite3` |
| [`backend/api/schemas.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/api/schemas.py) | Pydantic request/response model schemas | Python | **Critical** | `pydantic` |
| [`backend/separation/demucs_separator.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/separation/demucs_separator.py) | 4-stem neural source separator | Python | **Critical** | `demucs`, `torch` |
| [`backend/beats/beat_tracker.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/beats/beat_tracker.py) | Ellis dynamic programming beat tracking | Python | **Critical** | `librosa` |
| [`backend/meter/meter_detector.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/meter/meter_detector.py) | 6-meter metric classifier (2/4 - 12/8) | Python | **Critical** | `numpy`, `scipy` |
| [`backend/chord_recognition/btc_recognizer.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/chord_recognition/btc_recognizer.py) | BTC Transformer inference & ensemble fusion | Python | **Critical** | `torch`, `onnxruntime` |
| [`backend/bass/inversion_detector.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/bass/inversion_detector.py) | Sub-bass fundamental tracking & slash chords | Python | **Critical** | `scipy`, `numpy` |
| [`backend/export/pdf_exporter.py`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/backend/export/pdf_exporter.py) | ReportLab single-page lead sheet generator | Python | **Critical** | `reportlab` |
| [`shared/music_schema/song_analysis.schema.json`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/shared/music_schema/song_analysis.schema.json) | Shared cross-platform JSON data contract | JSON | **Critical** | Schema standard |
| [`mobile/flutter_app/lib/main.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/main.dart) | Flutter application entrypoint & theme | Dart | **Critical** | `flutter` |
| [`mobile/flutter_app/lib/screens/home_screen.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/screens/home_screen.dart) | Mobile dashboard & audio file selection | Dart | **Critical** | `file_picker` |
| [`mobile/flutter_app/lib/screens/chord_sheet_screen.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/screens/chord_sheet_screen.dart) | Responsive 2-column chord grid & playback UI | Dart | **Critical** | `audioplayers` |
| [`mobile/flutter_app/lib/screens/settings_screen.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/screens/settings_screen.dart) | Connection modes (Local, Remote, Auto) | Dart | **Critical** | `shared_preferences` |
| [`mobile/flutter_app/lib/services/server_config_service.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/services/server_config_service.dart) | URL resolution & auto-failover state machine | Dart | **Critical** | `http` |
| [`mobile/flutter_app/lib/services/export_service.dart`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/mobile/flutter_app/lib/services/export_service.dart) | Vector PDF export with Fit-to-Page algorithm | Dart | **Critical** | `pdf` |
| [`electron/main.cjs`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/electron/main.cjs) | Desktop shell, port discovery, process manager | JavaScript | **Optional** | `electron` |
| [`scripts/start_tunnel.bat`](file:///c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/scripts/start_tunnel.bat) | Cloudflare Tunnel launch script | Batch | **Optional** | `cloudflared.exe` |
