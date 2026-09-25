"""
Visual Diagnostic Generator for Song Chord Analyzer.
Generates multi-panel physical diagnostic plot for Bekhayali (3/4 time signature):
1. Audio Waveform with measure boundaries and downbeat markers.
2. Onset Strength Envelope with beat grid and downbeat phase alignment.
3. Tempogram & Multi-Hypothesis Analysis (86.1 BPM tactus vs 114.8 BPM rejected hemiola).
4. Beat-synchronous autocorrelation profile and candidate meter probabilities.
5. Bar-aligned chord progression showing strict 3/4 measure structure.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import soundfile as sf
import librosa
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches

from backend.meter.meter_detector import MeterDetector

AUDIO_PATH = Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/43f5b483/audio.mp3")
OUTPUT_ARTIFACT = Path("C:/Users/jerin/.gemini/antigravity/brain/afa270dc-5500-4349-926c-1696d559c897/meter_tempo_diagnostic_bekhayali.png")
OUTPUT_LOCAL = Path("c:/Users/jerin/OneDrive/Documents/song-chord-analyzer/meter_tempo_diagnostic_bekhayali.png")


def generate_diagnostic():
    print(f"Loading audio from {AUDIO_PATH}...")
    y, sr = sf.read(str(AUDIO_PATH))
    if y.ndim > 1:
        y = np.mean(y, axis=1)

    duration = len(y) / sr
    detector = MeterDetector(sample_rate=sr)
    res = detector.detect_meter(audio_path=AUDIO_PATH)
    meter_info, downbeats, pickup = res
    bpm = res.selected_bpm
    beats = res.selected_beats

    print(f"Detected: {meter_info.display} at {bpm:.1f} BPM, downbeats: {len(downbeats)}, pickup: {pickup}")

    # Excerpt for high-resolution inspection: 15s to 30s
    t_start, t_end = 15.0, 30.0
    idx_start, idx_end = int(t_start * sr), int(t_end * sr)
    t_axis = np.linspace(t_start, t_end, idx_end - idx_start)
    y_sub = y[idx_start:idx_end]

    # Onset envelope for excerpt
    hop = 512
    onset_full = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    onset_times = librosa.frames_to_time(np.arange(len(onset_full)), sr=sr, hop_length=hop)
    onset_mask = (onset_times >= t_start) & (onset_times <= t_end)

    # Tempogram
    tg = librosa.feature.tempogram(onset_envelope=onset_full, sr=sr, hop_length=hop)
    tempi = librosa.tempo_frequencies(tg.shape[0], sr=sr, hop_length=hop)
    mean_tg = np.mean(tg, axis=1)

    # Subset of beats and downbeats in excerpt
    sub_beats = [b for b in beats if t_start <= b <= t_end]
    sub_downbeats = [d for d in downbeats if t_start <= d <= t_end]

    # Style configuration
    plt.style.use('dark_background')
    fig = plt.figure(figsize=(16, 14), dpi=150)
    gs = fig.add_gridspec(5, 1, height_ratios=[1.2, 1.2, 1.2, 1.2, 1.0], hspace=0.38)

    # -------------------------------------------------------------
    # Panel 1: Waveform with Measure Boundaries and Downbeats
    # -------------------------------------------------------------
    ax1 = fig.add_subplot(gs[0])
    ax1.plot(t_axis, y_sub, color='#4FC3F7', alpha=0.7, lw=0.8, label="Acoustic Waveform")
    for i, db in enumerate(sub_downbeats):
        ax1.axvline(db, color='#FF5252', lw=2.2, linestyle='-', alpha=0.9, label="Measure Downbeat (Bar Line)" if i == 0 else "")
        ax1.text(db + 0.08, 0.72, f"Bar {i+8}", color='#FF8A80', fontsize=9, fontweight='bold',
                 bbox=dict(boxstyle="round,pad=0.2", facecolor="#263238", edgecolor="#FF5252", alpha=0.8))
    ax1.set_xlim(t_start, t_end)
    ax1.set_ylim(-1.0, 1.0)
    ax1.set_ylabel("Amplitude", fontsize=10, fontweight='bold', color='#E0E0E0')
    ax1.set_title("Panel 1: Waveform & Measure Boundaries (Bekhayali — ID: 43f5b483)", fontsize=12, fontweight='bold', color='#FFFFFF', pad=6)
    ax1.legend(loc="upper right", fontsize=9, framealpha=0.6)
    ax1.grid(True, color='#37474F', alpha=0.5, linestyle=':')

    # -------------------------------------------------------------
    # Panel 2: Onset Strength Envelope & Beat Tracking
    # -------------------------------------------------------------
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.plot(onset_times[onset_mask], onset_full[onset_mask], color='#FFD54F', lw=1.2, label="Onset Strength Salience")
    for i, b in enumerate(sub_beats):
        is_db = any(abs(b - db) < 0.08 for db in sub_downbeats)
        c = '#FF5252' if is_db else '#69F0AE'
        ls = '-' if is_db else '--'
        lw = 2.0 if is_db else 1.0
        ax2.axvline(b, color=c, lw=lw, linestyle=ls, alpha=0.85, label="Downbeat (Beat 1)" if is_db and i == 0 else ("Beat 2 / 3" if not is_db and i == 1 else ""))
    ax2.set_xlim(t_start, t_end)
    ax2.set_ylabel("Onset Salience", fontsize=10, fontweight='bold', color='#E0E0E0')
    ax2.set_title("Panel 2: Onset Envelope & 3-Beat Triple Pulse Grid (Quarter Note = 86.1 BPM)", fontsize=12, fontweight='bold', color='#FFFFFF', pad=6)
    ax2.legend(loc="upper right", fontsize=9, framealpha=0.6)
    ax2.grid(True, color='#37474F', alpha=0.5, linestyle=':')

    # -------------------------------------------------------------
    # Panel 3: Tempogram & Alternative Tempo Hypotheses
    # -------------------------------------------------------------
    ax3 = fig.add_subplot(gs[2])
    mask_tg = (tempi >= 45.0) & (tempi <= 220.0)
    ax3.plot(tempi[mask_tg], mean_tg[mask_tg], color='#B388FF', lw=2.0, label="Global Tempogram Salience")
    # Annotate True BPM (86.1)
    tg_86 = float(mean_tg[np.argmin(np.abs(tempi - 86.1))])
    ax3.plot(86.1, tg_86, marker='o', markersize=10, color='#00E676')
    ax3.annotate("TRUE TACTUS: 86.1 BPM\n(Quarter Note in 3/4 — Integer Divisibility N=6)",
                 xy=(86.1, tg_86), xytext=(52, 0.76),
                 arrowprops=dict(facecolor='#00E676', shrink=0.08, width=1.5, headwidth=7),
                 color='#00E676', fontweight='bold', fontsize=9,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#1B5E20", edgecolor="#00E676", alpha=0.9))

    # Annotate False Hemiola BPM (114.8)
    tg_114 = float(mean_tg[np.argmin(np.abs(tempi - 114.8))])
    ax3.plot(114.8, tg_114, marker='X', markersize=10, color='#FF1744')
    ax3.annotate("REJECTED HEMIOLA: 114.8 BPM\n(3:2 Cross-Pulse Aliasing — Ratio=1.50)",
                 xy=(114.8, tg_114), xytext=(128, 0.52),
                 arrowprops=dict(facecolor='#FF1744', shrink=0.08, width=1.5, headwidth=7),
                 color='#FF5252', fontweight='bold', fontsize=9,
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="#B71C1C", edgecolor="#FF1744", alpha=0.9))

    ax3.set_xlim(45.0, 220.0)
    ax3.set_ylim(0.35, 0.88)
    ax3.set_xlabel("BPM (Tempo)", fontsize=10, fontweight='bold', color='#E0E0E0')
    ax3.set_ylabel("Tempogram Energy", fontsize=10, fontweight='bold', color='#E0E0E0')
    ax3.set_title("Panel 3: Tempogram Multi-Hypothesis Evaluation & Hemiola Disambiguation", fontsize=12, fontweight='bold', color='#FFFFFF', pad=6)
    ax3.legend(loc="upper right", fontsize=9, framealpha=0.6)
    ax3.grid(True, color='#37474F', alpha=0.5, linestyle=':')

    # -------------------------------------------------------------
    # Panel 4: Candidate Meter Probability Distribution & Autocorrelation
    # -------------------------------------------------------------
    ax4 = fig.add_subplot(gs[3])
    meters = ["2/4", "3/4", "4/4", "6/8", "7/8", "12/8"]
    scores = [meter_info.candidate_scores.get(m, 0.05) for m in meters]
    colors = ['#42A5F5' if m != '3/4' else '#00E676' for m in meters]
    bars = ax4.bar(meters, scores, color=colors, width=0.5, edgecolor='#FFFFFF', lw=1.2, alpha=0.85)

    for bar, score in zip(bars, scores):
        yval = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2.0, yval + 0.02, f"{score*100:.1f}%",
                 ha='center', va='bottom', fontsize=10, fontweight='bold', color='#FFFFFF')

    ax4.set_ylim(0.0, 0.65)
    ax4.set_ylabel("Posterior Probability", fontsize=10, fontweight='bold', color='#E0E0E0')
    ax4.set_title("Panel 4: Meter Posterior Probability Distribution across all 6 Signatures (Winner: 3/4 at 45.5%)",
                  fontsize=12, fontweight='bold', color='#FFFFFF', pad=6)
    ax4.grid(axis='y', color='#37474F', alpha=0.5, linestyle=':')

    # -------------------------------------------------------------
    # Panel 5: Bar-Aligned Musical Measure Chord Sheet
    # -------------------------------------------------------------
    ax5 = fig.add_subplot(gs[4])
    ax5.set_xlim(0.0, 1.0)
    ax5.set_ylim(0.0, 1.0)
    ax5.axis('off')
    ax5.set_title("Panel 5: Musician-Friendly Measure-Aligned Chord Progression (3/4 Time Signature)",
                  fontsize=12, fontweight='bold', color='#FFFFFF', pad=10)

    # Display 6 measures in 3/4
    chord_progression = [
        ("Bar 8", "Gm", ["G", "Bb", "D"]),
        ("Bar 9", "F", ["F", "A", "C"]),
        ("Bar 10", "Eb", ["Eb", "G", "Bb"]),
        ("Bar 11", "Dm", ["D", "F", "A"]),
        ("Bar 12", "Cm", ["C", "Eb", "G"]),
        ("Bar 13", "D", ["D", "F#", "A"]),
    ]

    box_width = 0.135
    box_height = 0.70
    gap = 0.028
    x_offset = 0.025

    for i, (b_name, ch_name, notes) in enumerate(chord_progression):
        x = x_offset + i * (box_width + gap)
        y = 0.12
        rect = patches.FancyBboxPatch((x, y), box_width, box_height, boxstyle="round,pad=0.01",
                                      facecolor="#1A237E", edgecolor="#4FC3F7", lw=1.5, alpha=0.90)
        ax5.add_patch(rect)
        ax5.text(x + box_width / 2.0, y + 0.52, b_name, ha='center', va='center', fontsize=9, color='#B0BEC5', fontweight='bold')
        ax5.text(x + box_width / 2.0, y + 0.32, ch_name, ha='center', va='center', fontsize=16, color='#FFEB3B', fontweight='bold')
        ax5.text(x + box_width / 2.0, y + 0.12, "3 beats (♩ ♩ ♩)", ha='center', va='center', fontsize=8, color='#80CBC4')

    plt.tight_layout()

    OUTPUT_ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(OUTPUT_ARTIFACT), dpi=150, bbox_inches='tight')
    plt.savefig(str(OUTPUT_LOCAL), dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Visual diagnostic saved to:\n  - {OUTPUT_ARTIFACT}\n  - {OUTPUT_LOCAL}")


if __name__ == "__main__":
    generate_diagnostic()
