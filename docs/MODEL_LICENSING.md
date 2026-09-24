# Model and Library Licensing Documentation

This document records the licensing, provenance, and commercial use considerations for all audio and machine learning models, libraries, and checkpoints used in **Song Chord Analyzer**.

---

## 1. Source Code vs. Model Checkpoints / Datasets

It is essential to distinguish between the **source code licenses** and the **pretrained model weights / datasets** licenses:

| Component | Type | License | Permitted Use |
|---|---|---|---|
| **Song Chord Analyzer** | Application Source Code | MIT License | Commercial & Non-Commercial |
| **BTC Architecture** | Source Code | MIT License | Commercial & Non-Commercial |
| **BTC Checkpoints** | Pretrained Weights (`btc_model_large_voca.pt`) | Research Checkpoint (Trained on Isophonics / RWC / Billboard) | Research & Personal Non-Commercial Use (or commercial where fair use / synthetic data applies) |
| **Demucs v4 Architecture** | Source Code | MIT License | Commercial & Non-Commercial |
| **Demucs Checkpoints** | Pretrained Weights (`htdemucs`) | CC BY-NC 4.0 (Trained on MusDB-HQ) | Non-Commercial Use Only without separate license |
| **Librosa / SciPy / NumPy** | Core Signal Processing | BSD 3-Clause / ISC | Fully Permissive for Commercial & Non-Commercial Use |
| **FFmpeg** | Audio Transcoding & Decoding | LGPL v2.1+ / GPL v3.0 | Dynamically invoked via standalone executable process (no static linking) |
| **ReportLab** | PDF Generation Engine | BSD License | Permissive for Commercial & Non-Commercial Use |
| **FastAPI / Uvicorn / Starlette** | Backend REST Server | MIT / BSD 3-Clause | Fully Permissive for Commercial & Non-Commercial Use |
| **React / Vite / Tailwind** | Frontend Desktop UI | MIT License | Fully Permissive for Commercial & Non-Commercial Use |

---

## 2. BTC (Bi-directional Transformer for Chord Recognition)
- **Model Name:** BTC (Bi-directional Transformer for Chord Recognition)
- **Repository:** https://github.com/jayg996/BTC-ISMIR19
- **Authors:** Jonggook Park, Kyogu Lee (Music and Audio Research Group, Seoul National University, ISMIR 2019)
- **Code License:** MIT License (Permissive, allows commercial and non-commercial distribution)
- **Pretrained Checkpoint:** `btc_model_large_voca.pt` (170-chord vocabulary)
- **Training Datasets:** Isophonics (Beatles, Queen, Zweieck), RWC-Popular, McGill Billboard
- **Dataset Licensing & Commercial Notes:** The underlying datasets are standard MIR research corpora. In this application, BTC is isolated behind the `ChordRecognizer` abstract base class (`backend/chord/base.py`), enabling hot-swapping with commercial or proprietary models (such as Chordino, CREMA, or custom-trained CRNN models) without modifying any downstream pipeline logic.

---

## 3. Demucs (Hybrid Transformer Music Source Separation)
- **Model Name:** Demucs v4 / HTDemucs
- **Repository:** https://github.com/facebookresearch/demucs
- **Authors:** Alexandre Défossez, Nicolas Usunier et al. (Meta AI Research)
- **Code License:** MIT License
- **Pretrained Checkpoints:** `htdemucs` (4 stems: drums, bass, other, vocals)
- **Checkpoint License:** Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) for standard MusDB18-HQ weights.
- **Dynamic Runtime Resolution:** The application dynamically detects any local stem separation environment (e.g., `%APPDATA%\StemKit\venv\Scripts\python.exe` or `%LOCALAPPDATA%\Programs\stemkit`) or bundled fallback. The separation layer is wrapped behind `StemSeparator` (`backend/separation/demucs_separator.py`), which allows swapping in commercially unencumbered models (e.g. Spleeter [MIT], RoFormer [MIT], Open-Unmix [MIT]) at any time.

---

## 4. Audio & Signal Processing Libraries
- **Librosa:** Version 0.11.0. License: ISC License (BSD-compatible, fully permissive).
- **FFmpeg:** Version 9.0.2+. License: LGPL v2.1+ / GPL v3.0. Dynamic standalone binary execution via `subprocess`; conforms to LGPL decoupling requirements.
- **SoundFile:** Version 0.14.0. License: BSD 3-Clause License (Permissive).
- **SciPy / NumPy:** SciPy 1.17+, NumPy 1.26+. License: BSD 3-Clause License.
- **PyTorch / TorchAudio:** Version 2.5+. License: Modified BSD License.

---

## 5. Desktop Application & Frontend
- **Electron:** MIT License.
- **React 19:** MIT License.
- **Lucide Icons:** ISC License.
- **Tailwind CSS:** MIT License.

---

## 6. Architectural Modularity Guarantee
In compliance with project specifications:
- All models implement abstract base interfaces: `ChordRecognizer`, `StemSeparator`, `BeatTracker`, `KeyDetector`, `SectionDetector`.
- No single model is hardcoded as an immutable dependency.
- The pipeline provides pure CPU fallback and supports alternative recognizers.
