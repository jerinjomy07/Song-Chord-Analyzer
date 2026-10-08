# Known Limitations & Technical Risk Disclosure

To ensure complete architectural clarity, this document lists all known operational boundaries, hardware prerequisites, and intentional constraints in Song Chord Analyzer.

---

## 1. Operational & Architectural Boundaries

1. **Host Laptop Compute Dependency:**
   - For *new* audio analyses, the Android mobile application requires a running instance of the Python backend on the host computer. The phone does not execute the heavy Demucs/BTC neural networks locally.
2. **Personal Compute Server vs. Cloud:**
   - Remote Internet mode (via Cloudflare Tunnel) connects the phone to the user's personal laptop. It is **not a shared cloud SaaS cluster**. If the host laptop is powered down or enters sleep mode, remote analysis requests will time out.
3. **Queue Concurrency Cap:**
   - To safeguard consumer GPU memory (e.g. 6 GB VRAM), the backend enforces `MAX_ACTIVE_ANALYSES = 2` with a single-worker executor (`ThreadPoolExecutor(max_workers=1)`). Simultaneous submissions are queued; attempts beyond the queue limit receive HTTP 503.
4. **Very Long Audio Files ($> 15 	ext{ Minutes}$):**
   - Full 44.1 kHz stereo audio arrays for tracks longer than 15 minutes can consume $> 4 	ext{ GB}$ of RAM during Demucs separation. Standard songs (2 to 7 minutes) process in 15–25 seconds.
5. **Acoustic Mix Quality Dependencies:**
   - Severely degraded mono recordings, live bootlegs with extreme audience reverberation, or heavily detuned historical recordings (e.g. A4 $
e 440 	ext{ Hz}$) may exhibit reduced chord confidence.
6. **YouTube Direct Audio Extraction:**
   - The production analysis contract requires user-supplied local audio files. While YouTube metadata lookup exists, automated remote audio extraction is not part of the active pipeline.
