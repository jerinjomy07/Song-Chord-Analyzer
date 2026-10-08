# Diagnostic & Troubleshooting Runbooks

This guide provides practical, step-by-step solutions for common failure scenarios across mobile, desktop, and server environments.

---

## Runbook 1: Android App Cannot Connect to Server

```
[Android Connection Failed]
         │
         ├──► 1. Check Connection Mode (Settings Screen)
         │       Is mode set to Local, Remote, or Auto?
         │
         ├──► 2. If in LOCAL LAN Mode:
         │       • Verify phone and laptop are on the EXACT SAME Wi-Fi network.
         │       • Verify laptop IP: Run 'ipconfig' in PowerShell.
         │       • In Settings, update URL: http://<laptop_ip>:8000
         │       • Tap 'Test Connection'.
         │       • If timeout occurs: Check Windows Firewall. Run:
         │         netsh advfirewall firewall add rule name="Song Chord Analyzer" dir=in action=allow protocol=TCP localport=8000
         │
         └──► 3. If in REMOTE TUNNEL Mode:
                 • Verify Cloudflare Tunnel is running: Run 'scripts/start_tunnel.bat'.
                 • Look for the 'https://*.trycloudflare.com' URL in the terminal.
                 • Paste that exact URL into Android Settings -> Remote URL.
                 • Verify phone has working cellular (4G/5G) or Wi-Fi data.
```

---

## Runbook 2: Analysis Job Fails or Hangs

1. **Check Server Terminal Output:** The backend prints real-time stage progress:
   `[SEPARATING] 15%`, `[ANALYZING_BEATS] 45%`, `[ANALYZING_CHORDS] 60%`.
2. **GPU Out of Memory (CUDA OOM):**
   - Symptom: Error log contains `torch.cuda.OutOfMemoryError`.
   - Resolution: Ensure no other GPU-heavy software (games, 3D renderers) is active. The engine automatically releases VRAM between stages, but requires ~3.5 GB free VRAM during Demucs stem separation.
   - Fallback: To run on CPU, pass `--device cpu` or run without CUDA drivers.
3. **Queue Full (HTTP 503):**
   - Symptom: App reports "Analysis queue is full".
   - Cause: More than 2 analysis jobs submitted simultaneously.
   - Resolution: Wait for the current song analysis to complete before uploading another track.
