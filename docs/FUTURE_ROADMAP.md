# Future Architecture & Engineering Roadmap

This document outlines the strategic evolutionary milestones for Song Chord Analyzer.

---

## Phase 1: Current Architecture (Validated Foundation)
- ✓ Authoritative Windows Python MIR engine with Demucs v4 and BTC Transformer.
- ✓ Verified 21/21 parity on golden tracks with 0.000000s timing variance.
- ✓ Dual-mode networking (Local Wi-Fi + Remote Cloudflare Tunnel) with Auto failover.
- ✓ Responsive 2-column mobile chord sheet grid and adaptive 1-page PDF export.
- ✓ 100% offline playback, transposition, and local SQLite history.

---

## Phase 2: Next Milestones (Enhanced Production)
- [ ] **Dedicated Cloud VM Deployment:** Package the backend Docker container into an always-on cloud instance (e.g. AWS EC2 G4dn or Fly.io GPU) providing 24/7 global mobile analysis without requiring a personal laptop.
- [ ] **User Accounts & Cross-Device Cloud Sync:** Optional user authentication enabling automatic synchronization of analyzed songs between phone and desktop.
- [ ] **macOS & Linux Desktop Builds:** Compile standalone Electron/Python distributions for macOS (Apple Silicon M-series) and Linux.

---

## Phase 3: Long-Term Vision (Autonomous On-Device AI)
- [ ] **Mobile NPU Quantized Inference:** As mobile smartphone Neural Processing Units (NPUs) reach $\ge 8 	ext{ GB}$ unified memory, evaluate lightweight mobile stem models (e.g. MobileNet-Demucs) to achieve true offline on-device analysis.
- [ ] **Real-Time Microphone Chord Listening:** Live acoustic chord recognition listening via device microphone for real-time jamming and performance accompaniment.
