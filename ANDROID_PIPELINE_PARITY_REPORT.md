# Android vs Windows Music Analysis Pipeline Parity Report

## Executive Summary
Following the audit of the Android analysis engine, stage-by-stage remediation was initiated against the Windows reference implementation.

Stages 1 through 7 have now been completed, tested, and mathematically validated against the Windows reference engine on the golden song **Bekhayali** (`storage/cache/ecdbc4dd2a6d827b_22k_mono.wav`).

---

## 1. Stage-by-Stage Implementation & Parity Results

### Stage 1: Audio Normalization
* **Problem in Android:** Audio decoded via `MediaCodec` or WAV reader was left unscaled. Windows applies `soundfile_load_normalized`, which rescales peak amplitude to `0.95`. On Android, lower-volume audio files produced compressed CQT magnitudes and tripped threshold cutoffs.
* **Correction Applied:** In [`AudioDecoder.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/AudioDecoder.kt), added `normalizePcm()` to scale peak amplitude to `0.95` when peak $> 10^{-4}$ (preserving pure silence).
* **Measured Result on Bekhayali:**
  - Audio Peak Before: `0.950012`
  - Audio Peak After: `0.950000` (Exact target achieved)

---

### Stage 2: Fix Key Detection
* **Problem in Android:**
  - **Tritone Scrambling Bug:** [`KeyDetector.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/KeyDetector.kt) mapped CQT bins using `chroma[b % 12] += mag`. The 144-bin CQT has 24 bins per octave (2 bins per semitone). As a result, bin 0 (C) and bin 12 (F#, a tritone away) mapped to the same pitch class, completely scrambling the chromagram.
  - **Missing Dual-Scoring:** Android evaluated only single-profile correlation. Windows fuses Profile correlation (60%) and Triad energy concentration (40%) with margin-based confidence.
* **Correction Applied:**
  - Fixed mapping to `(b / 2) % 12`.
  - Added L2-normalization of the 12-element chroma vector.
  - Implemented dual-scoring: 60% Krumhansl-Schmuckler profile correlation + 40% Triad energy concentration.
  - Added margin-based key confidence calculation.
* **Measured Result on Bekhayali:**
  - **Windows Reference Key:** `Bb Minor` (confidence: `0.75`)
  - **Old Android (b % 12) Key:** `Ab Major` (confidence: `0.68`) ❌ **WRONG**
  - **Corrected Android Key:** `Bb Minor` (confidence: `0.72`)  **EXACT MATCH**
  - **Chroma Pitch-Class Mean Absolute Error:** `0.0344`
  - **Diagnostic Report:** [`tests/android_parity/key_parity_report.json`](tests/android_parity/key_parity_report.json)

---

### Stage 3: CQT Parity Diagnostic
* **Problem in Android:**
  - Lower octaves have slightly fewer frames due to decimation edge rounding. Android was clamping `frameIdx = min(f, octFrames - 1)`, creating duplicated frames and phase misalignment at the ends of lower octaves.
* **Correction Applied:**
  - In [`CqtExtractor.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/CqtExtractor.kt), implemented Librosa's exact `__trim_stack` behavior: `minFrames = min across all 6 octaves`.
* **Measured Result on Bekhayali (20-second excerpt):**
  - **Windows Feature Shape:** `(216, 144)`
  - **Android Feature Shape:** `(216, 144)`
  - **Frame Alignment Difference:** **0 frames** (Exact 1:1 match)
  - **Mean Absolute Error (MAE):** **`0.00524`**
  - **Feature Correlation:** **`0.99970`** (Exceeds $> 0.98$ target; mathematically near-identical)
  - **Diagnostic Report:** [`tests/android_parity/cqt_parity_report.json`](tests/android_parity/cqt_parity_report.json)

---

### Stage 4: Spectral-Flux Log-Mel Onset Envelope
* **Problem in Android:**
  - Android was using a crude broadband time-domain energy derivative $\max(0, E_t - E_{t-1})$, which is completely blind to spectral redistribution, pitch shifts, and note attacks with constant overall loudness.
* **Correction Applied:**
  - Created [`MelConstants.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/MelConstants.kt) with precomputed 128-band Slaney Mel filterbank weights.
  - Implemented [`SpectralFluxOnset.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/SpectralFluxOnset.kt): 2048-point STFT, Hann window, reflect padding (`pad=1024`), dB compression (`top_db=80.0`, `amin=1e-10`), first-order positive spectral difference across mel bands, and leading 3-frame alignment padding.
* **Measured Result on Bekhayali (Full 271s Track):**
  - **Windows Reference Frames:** `11676`
  - **Android Engine Frames:** `11676`
  - **Frame Alignment Difference:** **0 frames**
  - **Mean Absolute Error (MAE):** **`0.000104`**
  - **Pearson Correlation:** **`0.999961`** (Near-perfect 1.0 correlation)
  - **Diagnostic Report:** [`tests/android_parity/onset_parity_report.json`](tests/android_parity/onset_parity_report.json)

---

### Stage 5: Multi-Hypothesis Tempo Estimation
* **Problem in Android:**
  - Android picked the single highest raw autocorrelation lag divided by sample rate, prone to octave jumps (halving/doubling) and compound meter confusion.
* **Correction Applied:**
  - In [`TempoAndMeterDetector.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/TempoAndMeterDetector.kt), ported the Windows multi-hypothesis architecture:
    - Fundamental subdivision pulse $\tau_e$ extraction in $[0.16s, 0.46s]$ from un-normalized autocorrelation.
    - Candidate tempi generated across $60/(2\tau_e)$, $60/(3\tau_e)$, $60/\tau_e$ and autocorrelation peaks, deduplicated within 3 BPM.
    - Full candidate evaluation using:
      1. `avg_onset_ratio` (energy concentration at beats vs background)
      2. Autocorrelation score at beat lag + harmonic support (2x and 3x bar lags)
      3. Inter-beat interval (IBI) regularity
      4. Tactus density Gaussian prior centered at 1.8 onsets/beat (using $\log_2$)
      5. Musical tempo prior centered at 115 BPM (using $\log_2$)
      6. Penalties for extreme densities, low autocorrelation, and hemiola.
* **Measured Result on Bekhayali:**
  - **Windows Reference BPM:** `86.10 BPM` (confidence: `0.99`)
  - **Android Detected BPM:** `86.10 BPM` (confidence: `0.99`)
  - **BPM Difference:** **`0.00 BPM`** (Exact match)
  - **Diagnostic Report:** [`tests/android_parity/tempo_parity_report.json`](tests/android_parity/tempo_parity_report.json)

---

### Stage 6: Real Dynamic Programming Beat Tracking (Ellis DP)
* **Problem in Android:**
  - Android was generating a fake synthetic isochronous grid: `var t = 0.5; while (t < duration) { beats.add(t); t += beatSec }`. Beats did not follow the audio, completely drifted from real drums/strums, and started in pure silence.
* **Correction Applied:**
  - Created [`EllisBeatTracker.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/EllisBeatTracker.kt) implementing Dan Ellis's (2007) dynamic programming algorithm:
    1. Standard-deviation AGC onset normalization.
    2. Local score smoothing with Gaussian window $\exp(-0.5 (k \cdot 32 / \text{fpb})^2)$.
    3. Dynamic programming forward recursion with tightness penalty $100 \cdot (\ln(i - \text{loc}) - \ln(\text{fpb}))^2$.
    4. Backlink assignment with $0.01 \times \max(\text{localscore})$ threshold.
    5. Backtracking from median-thresholded local maximum.
    6. Trimming of leading and trailing weak onsets using 5-point Hanning envelope.
* **Measured Result on Bekhayali (Full Track):**
  - **Windows Reference Beat Count:** `353 beats`
  - **Android Beat Count:** `353 beats`
  - **Beat Count Difference:** **0 beats**
  - **Windows First Beat:** `5.2477s` (Starts right on the first musical strum, skipping initial silence)
  - **Android First Beat:** `5.2477s` (Exact match)
  - **Mean Absolute Error (MAE):** **`0.00000 seconds`** (100% bit-for-bit identical timestamps)
  - **Max Absolute Error:** **`0.00000 seconds`**
  - **Diagnostic Report:** [`tests/android_parity/beat_parity_report.json`](tests/android_parity/beat_parity_report.json)

---

### Stage 7: Downbeat Phase & Multi-Meter Detection
* **Problem in Android:**
  - Android evaluated meter without acoustic bass support and picked phase over the fake synthetic beat grid.
* **Correction Applied:**
  - In [`TempoAndMeterDetector.kt`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/TempoAndMeterDetector.kt):
    - Added 4th-order Butterworth lowpass filter at 130 Hz via [`BassAndInversionAnalyzer.sosFilter`](mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/BassAndInversionAnalyzer.kt).
    - Fused onset envelope (55%) and acoustic bass energy (45%) into beat salience.
    - Evaluated all 6 supported meters (2/4, 3/4, 4/4, 6/8, 7/8, 12/8) with metric accent templates.
    - Selected optimal downbeat phase $\phi$ and downbeats aligned to real beat indices `beats[phi + k * i]`.
* **Measured Result on Bekhayali:**
  - **Windows Reference Meter:** `4/4`
  - **Android Detected Meter:** `4/4` (Exact match)
  - **Windows Downbeat Count:** `89 downbeats`
  - **Android Downbeat Count:** `89 downbeats`
  - **Count Difference:** **0 downbeats**
  - **Windows First Downbeat:** `5.2477s` (Phase $\phi = 0$)
  - **Android First Downbeat:** `5.2477s` (Phase $\phi = 0$)
  - **Mean Absolute Error (MAE):** **`0.00000 seconds`** (Exact match)
  - **Diagnostic Report:** [`tests/android_parity/downbeat_parity_report.json`](tests/android_parity/downbeat_parity_report.json)

---

## 2. Visual Diagnostic Verification

Below is the verified waveform, spectral flux onset envelope, tracked beats, and measure downbeats on **Bekhayali** (0–20s):

![Bekhayali Timing Diagnostic](file:///C:/Users/jerin/.gemini/antigravity/brain/afa270dc-5500-4349-926c-1696d559c897/timing_diagnostic_bekhayali.png)

---

## 3. Updated Parity Status Matrix

| Stage | Component | Pre-Audit Status | Current Status | Parity Result |
| :--- | :--- | :---: | :---: | :--- |
| **Stage 1** | Audio Normalization | ❌ Missing |  **Resolved** | Peak scaled to 0.95 |
| **Stage 2** | Key Detection | 🐛 Broken (`Ab Major`) |  **Resolved** | `Bb Minor` (Exact match) |
| **Stage 3** | CQT Spectrogram | ⚠ Misaligned |  **Resolved** | Correlation: 0.9997, 0 frame diff |
| **Stage 4** | Spectral-Flux Onset | 🐛 Energy derivative |  **Resolved** | Correlation: 0.99996, MAE: 0.00010 |
| **Stage 5** | Multi-Hypothesis Tempo | 🐛 Raw lag peak |  **Resolved** | 86.10 BPM vs 86.10 BPM (0.0 diff) |
| **Stage 6** | Ellis DP Beat Tracking | 🐛 Synthetic isochronous loop |  **Resolved** | 353/353 beats, 0.0000s MAE, first beat @ 5.25s |
| **Stage 7** | Downbeat & Meter | 🐛 Shifted phase & toy AC |  **Resolved** | 4/4 meter, 89/89 downbeats, 0.0000s MAE |
| **Stage 8** | Chord Fusion & Smoothing | ⏳ Next | In Queue | Beat-synchronous pooling & PostProcessor |

---

## 4. Next Step
Proceed to Stage 8 (Beat-synchronous Chord Probability Pooling & Chord Post-Processing / Smoothing) to align the BTC transformer inferences with the validated beat/bar grid.
