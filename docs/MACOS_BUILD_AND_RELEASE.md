# macOS Build, Packaging & Release Guide
**Song Chord Analyzer — Standalone macOS Desktop (.dmg) Packaging**

---

## 1. Overview & Build Host Requirements

Song Chord Analyzer macOS release packages the complete, offline desktop application into an Apple Disk Image (`.dmg`) and compressed archive (`.zip`).

### Host Platform Compatibility
| Host OS | Can Build macOS App? | Notes |
| :--- | :--- | :--- |
| **macOS (Apple Silicon M1/M2/M3/M4)** | **Native (Recommended)** | Builds universal/arm64 DMG, signs, notarizes, and executes parity tests directly on Metal GPU. |
| **macOS (Intel x86_64)** | **Native** | Builds x64 or cross-compiles arm64 DMG; requires Rosetta 2 or cross-tooling. |
| **GitHub Actions (`macos-14`)** | **Automated CI (Recommended)** | Runs on Apple Silicon M1 hardware in the cloud, builds DMG, runs tests, signs, and notarizes. |
| **Windows / Linux** | **Partial / Preparation Only** | Can compile frontend (`npm run build`) and validate cross-platform Python code, but **cannot** invoke Apple's `hdiutil`, `codesign`, or `notarytool`. |

---

## 2. Prerequisites (on macOS Build Host)

1. **Xcode Command Line Tools:**
   ```bash
   xcode-select --install
   ```
2. **Node.js (v20+ LTS) & npm:**
   ```bash
   brew install node@20
   node -v  # v20.x.x
   npm -v   # 10.x.x
   ```
3. **Python 3.10 / 3.11 & Virtual Environment Tools:**
   ```bash
   brew install python@3.11
   ```
4. **Mach-O FFmpeg Binary:**
   - Universal or ARM64 FFmpeg static binary placed at `resources/ffmpeg/ffmpeg` with executable permissions (`chmod +x resources/ffmpeg/ffmpeg`).
   - Or install via Homebrew: `brew install ffmpeg`.

---

## 3. Python Runtime Packaging Strategy

macOS Monterey 12.3+ removed the built-in system Python (`/usr/bin/python`). To ensure 100% offline functionality without requiring users to install Python or open Terminal:

### Strategy: Standalone Embedded Python (`python-build-standalone`)
1. Download official Greg Hurrell / Astral `python-build-standalone` for `aarch64-apple-darwin` (or `x86_64-apple-darwin` for Intel):
   ```bash
   # Example for Apple Silicon (ARM64)
   curl -LO https://github.com/astral-sh/python-build-standalone/releases/download/20240224/cpython-3.11.8+20240224-aarch64-apple-darwin-install_only.tar.gz
   mkdir -p resources/python
   tar -xzf cpython-3.11.8+20240224-aarch64-apple-darwin-install_only.tar.gz -C resources/python --strip-components=1
   ```
2. Install offline wheel bundle into embedded runtime:
   ```bash
   resources/python/bin/pip3 install --no-cache-dir \
       torch torchaudio \
       demucs \
       librosa soundfile scipy numpy \
       fastapi uvicorn jsonschema pydantic
   ```
3. Ensure bundled model checkpoints exist:
   - `models/btc_model.pt` (BTC Transformer weights)
   - Demucs checkpoint cache in `resources/models/demucs/`

---

## 4. Building the Application

### 4.1 Compile Frontend Assets
```bash
# In repository root
npm ci
cd frontend
npm ci
npm run build
cd ..
```
This generates the optimized production bundle in `frontend/dist/`.

### 4.2 Packaging via Electron Builder
Execute the macOS distribution script defined in `package.json`:

```bash
# Build Apple Silicon (ARM64) DMG & ZIP
npm run dist:mac

# Or build both ARM64 and Intel x64
npm run dist:mac:all
```

Outputs will be generated in `dist_electron/`:
* `dist_electron/SongChordAnalyzer-1.0.0-arm64.dmg` (~1.2 - 1.8 GB with embedded PyTorch + Demucs models)
* `dist_electron/SongChordAnalyzer-1.0.0-arm64-mac.zip`

---

## 5. Apple Code Signing & Notarization

To allow macOS users to launch the application without Gatekeeper blocking ("App is damaged" or "Unidentified Developer"):

### 5.1 Environment Variables
Set the following secrets in your shell or CI/CD environment:
```bash
export APPLE_ID="developer@example.com"
export APPLE_APP_SPECIFIC_PASSWORD="abcd-efgh-ijkl-mnop"
export APPLE_TEAM_ID="ABC123XYZ"
export CSC_LINK="path/to/developer_id_application.p12"  # or base64
export CSC_KEY_PASSWORD="cert_password"
```

### 5.2 Hardened Runtime & Entitlements
Electron Builder automatically reads `build/entitlements.mac.plist` which grants:
* `com.apple.security.cs.allow-jit` (required for PyTorch JIT execution)
* `com.apple.security.cs.allow-unsigned-executable-memory` (required for PyTorch tensor allocations)
* `com.apple.security.cs.disable-library-validation` (allows loading bundled Python native wheels)
* `com.apple.security.network.client` & `server` (allows internal loopback IPC on 127.0.0.1:8000)

### 5.3 Manual Notarization & Stapling (If required)
```bash
# 1. Submit DMG to Apple Notary Service
xcrun notarytool submit dist_electron/SongChordAnalyzer-1.0.0-arm64.dmg \
    --apple-id "$APPLE_ID" \
    --password "$APPLE_APP_SPECIFIC_PASSWORD" \
    --team-id "$APPLE_TEAM_ID" \
    --wait

# 2. Staple ticket to DMG
xcrun stapler staple dist_electron/SongChordAnalyzer-1.0.0-arm64.dmg

# 3. Verify stapling
spctl --assess --type open --context context:primary-signature dist_electron/SongChordAnalyzer-1.0.0-arm64.dmg
```

---

## 6. Local Testing on macOS Without Code Signing

For local testing on an Apple Mac when you do not possess an active Apple Developer ID certificate:

1. Mount the generated DMG:
   ```bash
   hdiutil attach dist_electron/SongChordAnalyzer-1.0.0-arm64.dmg
   ```
2. Drag `SongChordAnalyzer.app` to `/Applications`.
3. Unmount the DMG:
   ```bash
   hdiutil detach /Volumes/SongChordAnalyzer*
   ```
4. Strip the quarantine attribute assigned by macOS Gatekeeper:
   ```bash
   xattr -cr /Applications/SongChordAnalyzer.app
   ```
5. Launch the application:
   ```bash
   open /Applications/SongChordAnalyzer.app
   ```

---

## 7. Verification Checklist

Before releasing a DMG build to users:
- [ ] Application launches cleanly from `/Applications` without Terminal prompts.
- [ ] Health check handshake succeeds within 5 seconds (`GET http://127.0.0.1:8000/api/health`).
- [ ] Audio upload and waveform rendering works with MP3, WAV, FLAC, M4A.
- [ ] Full Demucs separation and BTC chord inference completes locally without network requests.
- [ ] Sub-bass inversion tracking accurately reports slash chords (e.g., `C/E`, `G/B`).
- [ ] Multi-meter detector properly handles complex meters (e.g., `6/8`, `7/8`, `12/8`).
- [ ] Transposition (`+`/`-` semitones) updates chord display instantaneously.
- [ ] 1-page compact PDF export generates properly formatted sheets.
- [ ] Application quit terminates the local Python backend cleanly without leaving zombie processes.
