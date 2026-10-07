# Song Chord Analyzer — Dual Mode Demo Network Setup Guide

This document describes how to connect the Android application to the **authoritative Windows Python MIR server** using either:
1. **Local Network Mode (LAN / Wi-Fi)**: Direct local Wi-Fi connection. Works completely offline (no internet connection required as long as the router/hotspot connects phone and laptop).
2. **Remote Internet Mode (Cloudflare Tunnel)**: Public HTTPS tunnel allowing you to analyze songs from anywhere in the world over **4G / 5G cellular data or external Wi-Fi**, without paying for cloud servers or entering a credit card.

---

## Architecture Overview

```
                         ┌── Mode 1: Local Wi-Fi (LAN) ──────┐
                         │   http://192.168.x.x:8000         │
                         │                                   ▼
📱 ANDROID APP ──────────┤                              💻 LAPTOP
                         │                               FastAPI Server
                         │                               (Port 8000)
                         │                                   │
                         └── Mode 2: Remote Internet ──────►│
                             https://*.trycloudflare.com     │
                             (Encrypted Tunnel)              ▼
                                                    WINDOWS MIR ENGINE
                                                    (Demucs + BTC + CQT)
                                                             │
                                                             ▼
                                                    SongAnalysis JSON
                                                             │
                                                             ▼
                                                        📱 ANDROID APP
```

> [!IMPORTANT]
> **One Server. One Analysis Engine. Two Connection Methods.**
> All musical features (BPM, meter detection, beat grid, chord sheet, inversions) are computed identically on your laptop regardless of which connection mode is selected.

---

## Mode 1 — Local Network Setup (Wi-Fi / LAN)

### When to Use
- You and your laptop are in the same room / on the same Wi-Fi network.
- You have no internet access (e.g., local router or mobile hotspot with cellular data turned off).

### Step-by-Step Instructions

1. **Start the Local Server**:
   Double-click `scripts\start_server_local.bat` or run:
   ```powershell
   & "$env:USERPROFILE\AppData\Roaming\StemKit\venv\Scripts\python.exe" -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
2. **Identify Your Laptop's LAN IP**:
   The launcher script automatically displays your LAN IP. Alternatively, run in PowerShell:
   ```powershell
   (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like "192.168.*" -or $_.IPAddress -like "10.*" }).IPAddress
   ```
   *Example:* `192.168.0.180`
3. **Connect Your Phone**:
   Ensure your Android device is connected to the same Wi-Fi network or laptop mobile hotspot.
4. **Configure the App**:
   - Open the **Song Chord Analyzer** app on your phone.
   - Tap the **Settings** icon (top right).
   - Select **Local** mode.
   - Enter your Local Network URL: `http://192.168.0.180:8000` (substitute your real IP).
   - Tap **Test Connection**.
   - Confirm status shows: `Local Network: CONNECTED ✓` with latency in milliseconds.
   - Tap **Save Server Configuration**.
5. **Analyze Songs**:
   Return to Home and upload audio files or convert YouTube songs.

### Windows Firewall Configuration (One-time)
If the phone fails to connect, allow inbound TCP connections on port 8000 for Private networks:
```powershell
New-NetFirewallRule -DisplayName "Song Chord Analyzer (Port 8000 Local LAN)" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow -Profile Private
```

---

## Mode 2 — Remote Internet Setup (Cloudflare Tunnel)

### When to Use
- You are away from your laptop (at a rehearsal, studio, or traveling).
- Your phone is on **4G / 5G mobile data** or connected to an external Wi-Fi network.

### Operating Rules
- **Laptop Status:** Laptop must remain **powered ON** and **connected to the internet**.
- **Services:** Both FastAPI and Cloudflare Tunnel must remain running on the laptop.
- **Cost:** Exactly **₹0 / $0.00**. No credit card or cloud billing required.
- **Laptop Turned OFF:** Remote mode will cleanly report that the analysis server is unavailable.

### Step-by-Step Instructions

1. **Start Dual Demo Services**:
   Double-click `scripts\start_demo_dual.bat` (or `scripts\start_tunnel.bat` if the server is already running).
2. **Locate the Public HTTPS Tunnel URL**:
   The Cloudflare Tunnel terminal window will display:
   ```text
   Your quick Tunnel has been created! Visit it at:
   https://xxxx-xxxx-xxxx.trycloudflare.com
   ```
3. **Configure the App on Your Phone**:
   - Open **Settings** in the app.
   - Select **Remote** mode.
   - Enter the Remote Internet URL: `https://xxxx-xxxx-xxxx.trycloudflare.com`.
   - (Optional) Enter an API Key if configured on the server.
   - Tap **Test Connection**.
   - Confirm status shows: `Remote Internet: CONNECTED ✓`.
   - Tap **Save Server Configuration**.
4. **Analyze Songs Remotely**:
   Analyze songs normally from anywhere over mobile data.

---

## Mode 3 — Auto Detect Mode

### How it Works
1. When analyzing a song, the app probes the configured **Local Network URL** first (fast 1.8s timeout).
2. If reachable (e.g. you are at home on Wi-Fi), it connects via Local LAN.
3. If unreachable (e.g. you walked out of the house and switched to 4G), it immediately falls back to the **Remote Internet URL**.
4. The active connection banner on the Home screen displays whether you are currently connected via **LOCAL NETWORK** or **REMOTE INTERNET**.

---

## Security (Protecting Remote Endpoints)

To prevent unauthorized internet traffic from using your laptop's GPU/CPU compute through the public tunnel, you can configure an API key:

1. On the laptop, set the environment variable before launching the server:
   ```cmd
   set API_AUTH_KEY=MySecureDemoSecret123
   ```
2. In the Android App Settings:
   - Enter `MySecureDemoSecret123` into the **API Key** field.
3. Requests without this matching key will receive `HTTP 401 Unauthorized`.

---

## Offline Features (No Server Required)

Even when the laptop is turned completely OFF, previously analyzed songs remain 100% functional on the phone:
- Song History & Saved Library
- Interactive Chord Sheet & Section Navigation
- Audio Playback & Auto-scroll
- Transpose (+ / - semitones)
- Editing Chords & Renaming Sections
- Export to PDF, TXT, and JSON
