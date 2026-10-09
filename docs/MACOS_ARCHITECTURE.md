# macOS Desktop Architecture Specification
**Song Chord Analyzer — Standalone macOS Architecture & Runtime Design**

---

## 1. Executive Summary

This document specifies the architectural design for the standalone macOS desktop edition of **Song Chord Analyzer**. The macOS release delivers a self-contained, 100% offline, native desktop application packaged as an Apple Disk Image (`.dmg`) and compressed archive (`.zip`).

The macOS application operates completely autonomously without requiring:
* A remote Windows PC or development machine.
* External FastAPI or cloud server infrastructure.
* Cloudflare Tunnels, reverse proxies, or open network ports.
* Paid third-party APIs or cloud subscriptions.
* Active internet connectivity for audio analysis once installed.

The macOS application provides the identical musical intelligence, accuracy, and rich interactive interface as the reference Windows application, adhering strictly to the shared music schema contract (`shared/music_schema/song_analysis.schema.json`).

---

## 2. System Architecture & Topology

```
+--------------------------------------------------------------------------+
|                       macOS Desktop Application                          |
|                       (SongChordAnalyzer.app)                            |
+--------------------------------------------------------------------------+
|                                                                          |
|  +--------------------------------------------------------------------+  |
|  |                 Electron Main Process (Node.js)                   |  |
|  |  - Lifecycle Management (Launch, Monitor, Terminate)               |  |
|  |  - Window Management & Native macOS Menus                          |  |
|  |  - POSIX Child Process Management & Signal Handling                |  |
|  |  - Secure Loopback IPC Gateway (127.0.0.1)                         |  |
|  +--------------------------------------------------------------------+  |
|             |                                            |               |
|             | Loads UI HTML/JS                           | Spawns Child  |
|             v                                            v Process       |
|  +------------------------------------+    +---------------------------+ |
|  |     Electron Renderer Process      |    | Local Python MIR Engine   | |
|  |     (React / Vite Desktop UI)      |    | (FastAPI / Uvicorn)       | |
|  |  - Compact Chord Sheet             |    |  - MacOSAnalysisEngine    | |
|  |  - Audio Player & Waveform Sync    |    |  - Demucs v4 Separation   | |
|  |  - Auto-Scroll & Scrubber          |    |  - BTC Neural Transformer | |
|  |  - Real-time Transposition (b/#)   |    |  - Sub-Bass Inversions    | |
|  |  - Interactive Chord Editing       |    |  - Multi-Meter Tracking   | |
|  |  - Adaptive 1-Page PDF Export      |    |  - K-S Key Detection      | |
|  |  - Local History DB Browser        |    |  - Bar & Beat Alignment   | |
|  +------------------------------------+    +---------------------------+ |
|                   |                                      |               |
|                   +--- HTTP REST / SSE (127.0.0.1:8000) -+               |
|                                                                          |
+--------------------------------------------------------------------------+
```

---

## 3. Process Tree & Lifecycle Management

### 3.1 Startup Sequence

1. **User Action:** The user launches `/Applications/SongChordAnalyzer.app` via Finder, Dock, or Spotlight.
2. **Main Process Entry:** Electron's main process (`electron/main.cjs`) initializes.
3. **Environment Detection:**
   - Detects `process.platform === 'darwin'`.
   - Resolves application paths: bundled app root vs development directory.
   - Resolves standalone Python runtime:
     - Packaged: `process.resourcesPath/python/bin/python3`
     - System/VirtualEnv fallback: `~/.local/share/SongChordAnalyzer/venv/bin/python3` or Homebrew python.
   - Resolves FFmpeg binary:
     - Packaged: `process.resourcesPath/ffmpeg/ffmpeg` (Mach-O ARM64/Universal)
     - System fallback: `/opt/homebrew/bin/ffmpeg` or `/usr/local/bin/ffmpeg`.
4. **Backend Spawning:**
   - Electron spawns the backend child process via `child_process.spawn(pythonPath, ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'])`.
   - Process is launched in detached mode on POSIX (`detached: true`) within its own process group to ensure clean sub-process isolation and signal trapping.
5. **Health Check & Readiness Handshake:**
   - The UI displays a native macOS loading indicator: *"Initializing Neural MIR Engine..."*.
   - Electron polls `GET http://127.0.0.1:8000/api/health` with a 500ms interval (timeout 45s).
   - Once the health check returns `{ "status": "ok", "engine": "MacOSAnalysisEngine" }`, the main browser window transitions to the primary analysis workspace.

### 3.2 Security & Loopback Binding

* **Loopback Exclusivity:** In desktop mode on macOS, the backend is strictly bound to `127.0.0.1` (IPv4 loopback). It does **not** bind to `0.0.0.0` or broadcast over local Wi-Fi, preventing exposure on untrusted public networks.
* **CORS Policy:** FastAPI is configured to accept requests only from `vscode-file://`, `file://`, and `http://localhost:*` origins.
* **Process Sandboxing:** Python executes with user-level privileges under macOS App Sandbox guidelines, reading and writing only to dedicated user application support directories.

### 3.3 Shutdown & Clean Cleanup

To eliminate orphaned or zombie Python processes when quitting the application:
1. Electron hooks `app.on('before-quit')`, `app.on('will-quit')`, and uncaught process termination signals (`SIGINT`, `SIGTERM`).
2. Main process signals the backend child process:
   ```javascript
   // POSIX process group termination on macOS
   if (backendProcess && backendProcess.pid) {
     try {
       process.kill(-backendProcess.pid, 'SIGTERM');
     } catch (e) {
       backendProcess.kill('SIGTERM');
     }
   }
   ```
3. A grace period of 3,000ms is provided for PyTorch and SQLite to flush writes and release memory, followed by `SIGKILL` (`kill -9`) if the child process has not exited.

---

## 4. Hardware Acceleration & Memory Architecture

### 4.1 Apple Silicon Metal Performance Shaders (MPS)

macOS devices powered by Apple Silicon (M1, M2, M3, M4 family) feature high-bandwidth Unified Memory Architecture (UMA) shared between CPU and GPU cores.

* **Metal Backend:** PyTorch operations in Demucs separation and the BTC Transformer are executed using `torch.device("mps")` when `torch.backends.mps.is_available()` returns `True`.
* **Safe Fallback:** If an unsupported MPS tensor operation or dimension boundary is encountered, PyTorch's MPS fallback mechanism seamlessly falls back to CPU execution without aborting analysis or corrupting tensor results.
* **Parity Guarantee:** Model weights, normalization parameters, and activation functions remain 100% identical across CUDA, MPS, and CPU.

### 4.2 Unified Memory Management

Because Apple Silicon shares RAM between system and graphics contexts, memory bloat must be strictly controlled to prevent macOS memory pressure warnings:

1. **Stage-by-Stage VRAM/RAM Release:**
   - After stem separation completes, Demucs model weights are moved off-device and `torch.mps.empty_cache()` (or `gc.collect()`) is called.
   - After BTC chord probability extraction completes, neural weights are pruned from active memory before running temporal smoothing and beat-synchronous fusion.
2. **Audio Chunking:** Long audio files (> 10 minutes) are streamed in 30-second windows during CQT feature extraction to maintain a flat memory footprint (< 1.8 GB peak).

---

## 5. Storage Hierarchy & POSIX File System

The macOS version adheres to standard macOS Apple Human Interface Guidelines and XDG conventions for directory layout:

| Resource Type | Path on macOS | Purpose |
| :--- | :--- | :--- |
| **User Application Data** | `~/Library/Application Support/SongChordAnalyzer/` | Root storage for all user persistence |
| **Uploaded Audio** | `~/Library/Application Support/SongChordAnalyzer/uploads/` | Staged audio files awaiting analysis |
| **Separated Stems** | `~/Library/Application Support/SongChordAnalyzer/stems/<hash>/` | Demucs separated stems (bass & accompaniment) |
| **Analysis Cache** | `~/Library/Application Support/SongChordAnalyzer/cache/` | Normalized WAVs and pre-computed features |
| **History Database** | `~/Library/Application Support/SongChordAnalyzer/history.db` | Local SQLite database of analyzed songs |
| **PDF & TXT Exports** | `~/Library/Application Support/SongChordAnalyzer/exports/` | Generated chord sheet documents |
| **Application Logs** | `~/Library/Logs/SongChordAnalyzer/` | Diagnostic logging for backend and UI |
| **Temporary Files** | `/tmp/SongChordAnalyzer/` | Scratch buffers automatically cleaned on exit |

---

## 6. Algorithmic Parity Architecture

The macOS implementation utilizes `MacOSAnalysisEngine`, which implements `IAnalysisEngine` in `shared/analysis_contracts/analysis_engine.py`.

```
                    +--------------------+
                    |  IAnalysisEngine   |
                    | (Abstract Base)    |
                    +--------------------+
                              ^
              +---------------+---------------+
              |                               |
    +-----------------------+       +---------------------+
    | WindowsAnalysisEngine |       | MacOSAnalysisEngine |
    +-----------------------+       +---------------------+
              |                               |
              +---------------+---------------+
                              | Delegates To
                              v
                +---------------------------+
                |   SongAnalyzerPipeline    |
                +---------------------------+
                | 1. Audio Normalization    |
                | 2. Demucs Separation      |
                | 3. Multi-Meter Tracking   |
                | 4. BTC Neural Inference   |
                | 5. Sub-Bass Inversion     |
                | 6. Harmonic Fusion        |
                | 7. Bar Alignment          |
                | 8. Section Segmentation   |
                +---------------------------+
                              | Produces
                              v
                +---------------------------+
                |    SongAnalysis Schema    |
                |    (100% Shared JSON)     |
                +---------------------------+
```

### 6.1 Parity Guarantees

* **Zero Toy Analyzers:** The macOS version does **not** replace Demucs or BTC with simplified heuristic scripts. The complete 18-stage pipeline is executed locally.
* **Exact Multi-Meter Support:** Full classification across all 6 supported meters (`2/4`, `3/4`, `4/4`, `6/8`, `7/8`, `12/8`) with beat-synchronous bar alignment.
* **Physical Bass Inversion Tracking:** Sub-bass energy analysis tracking harmonic pitch inversions (`C/E`, `G/B`, `Am/G`) preserved verbatim.
* **Key & Mode:** Krumhansl-Schmuckler chroma correlation with mode detection (Major, Minor, Dorian, Mixolydian).

---

## 7. macOS Security, Notarization & Packaging

### 7.1 macOS Hardened Runtime Entitlements

The application is bundled with `build/entitlements.mac.plist` declaring entitlements required for high-performance PyTorch JIT compilation and local networking:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.cs.allow-jit</key>
    <true/>
    <key>com.apple.security.cs.allow-unsigned-executable-memory</key>
    <true/>
    <key>com.apple.security.cs.disable-library-validation</key>
    <true/>
    <key>com.apple.security.network.client</key>
    <true/>
    <key>com.apple.security.network.server</key>
    <true/>
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>
</dict>
</plist>
```

### 7.2 Gatekeeper & Code Signing

1. **Binary Signing:** All Mach-O executables (Python runtime, dylibs, FFmpeg, Electron binary) are recursively signed using `codesign --deep --options runtime`.
2. **Apple Notarization:** Packaged `.dmg` archives are submitted to the Apple Notary Service via `xcrun notarytool`.
3. **Stapling:** Notarization tickets are stapled directly to the `.dmg` using `xcrun stapler staple` so users can open the application without Gatekeeper blocking, even when completely offline.
