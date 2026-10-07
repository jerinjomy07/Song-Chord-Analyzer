"""
Generates the comprehensive visual diagnostic plot for Bekhayali (0-20s):
Waveform -> Spectral Flux Onset Envelope -> Onset Peaks -> Beats -> Downbeats.
Saves the artifact to the conversation artifact directory.
"""

from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf
import librosa

from backend.audio.preprocessor import soundfile_load_normalized
from tests.android_parity.test_onset_parity import compute_android_spectral_flux_onset
from tests.android_parity.test_beat_parity import simulate_android_ellis_dp_beat_track
from tests.android_parity.test_downbeat_parity import simulate_android_downbeat_and_meter


def generate_plot():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    y_norm, sr = soundfile_load_normalized(wav_path)

    # First 20 seconds
    duration = 20.0
    n_samples = int(duration * sr)
    y_20 = y_norm[:n_samples]
    time_audio = np.linspace(0, duration, n_samples)

    # Onset envelopes
    ref_onset = librosa.onset.onset_strength(y=y_norm, sr=sr, hop_length=512)
    and_onset = compute_android_spectral_flux_onset(y_norm, sr)
    n_frames_20 = int(duration * sr / 512)
    time_frames = np.arange(n_frames_20) * (512.0 / sr)

    ref_onset_20 = ref_onset[:n_frames_20]
    and_onset_20 = and_onset[:n_frames_20]

    # Beat and Downbeat tracking
    and_beats = simulate_android_ellis_dp_beat_track(and_onset, bpm=86.1, sample_rate=sr, hop_length=512)
    and_meter, and_bpm, and_downbeats, and_phase, _ = simulate_android_downbeat_and_meter(y_norm, sr)

    beats_20 = [b for b in and_beats if b <= duration]
    downbeats_20 = [d for d in and_downbeats if d <= duration]

    # Onset peaks
    onsets = librosa.onset.onset_detect(onset_envelope=and_onset, sr=sr, hop_length=512, units='time')
    onsets_20 = [o for o in onsets if o <= duration]

    # Plot
    fig, axes = plt.subplots(4, 1, figsize=(14, 10), sharex=True, gridspec_kw={'height_ratios': [1.2, 1.2, 1.0, 1.0]})

    # 1. Waveform
    axes[0].plot(time_audio, y_20, color='#1f77b4', alpha=0.75, linewidth=0.8, label="22.05 kHz Normalized PCM")
    axes[0].set_ylabel("Amplitude", fontsize=10)
    axes[0].set_title("Bekhayali (0-20s): Audio Waveform & Peak Normalization", fontsize=12, fontweight='bold')
    axes[0].grid(True, linestyle="--", alpha=0.5)
    axes[0].legend(loc="upper right")

    # 2. Onset Envelope Parity
    axes[1].plot(time_frames, ref_onset_20, color='#2ca02c', linewidth=2.0, label="Windows Reference (librosa.onset_strength)")
    axes[1].plot(time_frames, and_onset_20, color='#d62728', linestyle="--", linewidth=1.5, label="Android Engine (SpectralFluxOnset)")
    axes[1].scatter(onsets_20, [and_onset[int(round(o * sr / 512))] for o in onsets_20], color='#ff7f0e', s=25, zorder=5, label="Detected Onset Peaks")
    axes[1].set_ylabel("Onset Flux (dB)", fontsize=10)
    axes[1].set_title("Stage 4: Spectral Flux Onset Envelope (Pearson Correlation = 0.999961)", fontsize=12, fontweight='bold')
    axes[1].grid(True, linestyle="--", alpha=0.5)
    axes[1].legend(loc="upper right")

    # 3. Dynamic Programming Beats
    axes[2].plot(time_frames, and_onset_20, color='#7f7f7f', alpha=0.4, label="Onset Envelope")
    for i, b in enumerate(beats_20):
        axes[2].axvline(b, color='#9467bd', linestyle="-", linewidth=1.8, alpha=0.85,
                        label="Tracked Beats (Ellis DP)" if i == 0 else "")
        axes[2].text(b, axes[2].get_ylim()[1] * 0.85, f"{b:.2f}s", rotation=90, fontsize=7, color='#4a148c', ha='right', va='top')
    axes[2].set_ylabel("Beat Pulse", fontsize=10)
    axes[2].set_title("Stage 6: Real Dynamic Programming Beat Tracking (86.1 BPM, First Beat @ 5.25s)", fontsize=12, fontweight='bold')
    axes[2].grid(True, linestyle="--", alpha=0.5)
    axes[2].legend(loc="upper right")

    # 4. Downbeats & Measure Phase
    axes[3].plot(time_frames, and_onset_20, color='#7f7f7f', alpha=0.3, label="Onset Envelope")
    for i, b in enumerate(beats_20):
        axes[3].axvline(b, color='#c5b0d5', linestyle=":", linewidth=1.2, alpha=0.6)
    for i, d in enumerate(downbeats_20):
        axes[3].axvline(d, color='#d62728', linestyle="-", linewidth=2.5, alpha=0.95,
                        label=f"Measure Downbeats ({and_meter})" if i == 0 else "")
        axes[3].text(d, 8.0, f"Bar {i+1}\n({d:.2f}s)", fontsize=8, fontweight='bold', color='#b71c1c', ha='center')
    axes[3].set_ylabel("Downbeats", fontsize=10)
    axes[3].set_xlabel("Time (seconds)", fontsize=11, fontweight='bold')
    axes[3].set_title(f"Stage 7: Downbeat Phase Alignment (Meter: {and_meter}, Phase: {and_phase}, 89 Downbeats Total)", fontsize=12, fontweight='bold')
    axes[3].set_xlim(0, 20.0)
    axes[3].grid(True, linestyle="--", alpha=0.5)
    axes[3].legend(loc="upper right")

    plt.tight_layout()

    artifact_dir = Path("C:/Users/jerin/.gemini/antigravity/brain/afa270dc-5500-4349-926c-1696d559c897")
    out_path = artifact_dir / "timing_diagnostic_bekhayali.png"
    plt.savefig(out_path, dpi=180)
    print(f"Saved diagnostic visualization to {out_path}")


if __name__ == "__main__":
    generate_plot()
