# Live Demonstration Script & Presentation Guide

This document provides a field-tested procedure for demonstrating Song Chord Analyzer to musicians, evaluators, and stakeholders.

---

## Part 1: Local Network Demo (Home / Studio Rehearsal)

**Scenario:** Showing how a musician analyzes an MP3 file on their phone over local home Wi-Fi with zero internet access.

1. **Start Laptop Server:**
   - Double-click `run.bat` or run:
     ```powershell
     python run_app.py --no-browser
     ```
   - Confirm server initializes and prints: `Uvicorn running on http://0.0.0.0:8000`.
2. **Connect Phone:**
   - Connect phone to the same Wi-Fi network as the laptop.
   - Open Song Chord Analyzer on Android.
   - Tap **Settings** (gear icon) -> verify **Local Mode** is selected.
   - Tap **Test Connection** -> confirm green badge and latency ($< 30 	ext{ ms}$).
3. **Execute Analysis:**
   - Return to **Home Screen**.
   - Tap **Select Audio File** -> choose a demo MP3 file (e.g. *Bekhayali*).
   - Observe real-time progress bar updating through all 12 stages.
4. **Demonstrate Results:**
   - **Responsive 2-Column Grid:** Point out that each screen row shows two bars side-by-side, doubling visible chords.
   - **Playback Sync:** Press Play -> show the active chord chip lighting up and screen auto-scrolling.
   - **Transpose:** Tap Transpose -> adjust by $+2$ semitones -> show chords instantly update.
   - **1-Page PDF Export:** Tap Export PDF -> show that the entire song fits cleanly onto **one A4 page**.

---

## Part 2: Remote Cellular Demo (On-the-Go over 4G/5G)

**Scenario:** Proving that the user can analyze songs from anywhere in the world using cellular data while the laptop acts as the personal compute server.

1. **Launch Cloudflare Tunnel on Laptop:**
   - Run `scripts/start_tunnel.bat`.
   - Copy the public URL generated (e.g. `https://random-words.trycloudflare.com`).
2. **Configure Mobile App:**
   - Turn OFF Wi-Fi on the phone (switch to **Cellular 4G/5G**).
   - Open Song Chord Analyzer -> Settings -> select **Remote Mode**.
   - Paste the tunnel URL into **Remote URL**.
   - Tap **Test Connection** -> confirm green badge.
3. **Run Remote Analysis:**
   - Select an audio file on the phone.
   - Watch the laptop terminal light up with GPU tensor processing while the phone is completely on cellular data!
