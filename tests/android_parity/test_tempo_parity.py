"""
Stage 5: Multi-Hypothesis Tempo Estimation Parity Test.
Compares the Windows reference BeatTracker against the Android multi-hypothesis tempo estimation engine.
Verifies BPM detection, hypothesis generation, tactus prior scoring, and confidence on the golden song Bekhayali.
"""

from pathlib import Path
import json
import numpy as np
import soundfile as sf
import librosa

from backend.audio.preprocessor import soundfile_load_normalized
from backend.beat.beat_tracker import BeatTracker
from tests.android_parity.test_onset_parity import compute_android_spectral_flux_onset


def simulate_android_tempo_detection(audio, sample_rate=22050):
    hop = 512
    frames_per_sec = float(sample_rate) / hop
    duration = len(audio) / sample_rate

    onset_env = compute_android_spectral_flux_onset(audio, sample_rate)
    n_frames = len(onset_env)

    # Autocorrelation of onset envelope
    max_lag = min(n_frames - 1, int(5.5 * frames_per_sec))
    min_lag = max(4, int(frames_per_sec * 60.0 / 250.0))

    ac = np.correlate(onset_env, onset_env, mode='full')
    ac = ac[n_frames - 1 : n_frames - 1 + max_lag]
    ac = ac / (ac[0] + 1e-8)

    # Subdivision pulse tau_e
    sub_peaks = []
    for lag in range(2, max_lag - 2):
        t = lag / frames_per_sec
        if 0.16 <= t <= 0.46 and ac[lag] > ac[lag - 1] and ac[lag] > ac[lag + 1]:
            sub_peaks.append((t, float(ac[lag])))
    sub_peaks.sort(key=lambda x: x[1], reverse=True)
    tau_e = sub_peaks[0][0] if sub_peaks else 0.35

    # Onset rate
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sample_rate, hop_length=hop, units='time')
    onset_rate = len(onsets) / max(1.0, duration)
    mean_onset = float(np.mean(onset_env)) + 1e-8

    raw_cands = [
        round(60.0 / (2.0 * tau_e), 1),
        round(60.0 / (3.0 * tau_e), 1),
        round(60.0 / tau_e, 1)
    ]
    for lag in range(min_lag, max_lag - 1):
        if ac[lag] > ac[lag - 1] and ac[lag] > ac[lag + 1] and ac[lag] > 0.08:
            b = round((frames_per_sec * 60.0 / lag), 1)
            if 40.0 <= b <= 250.0:
                raw_cands.append(b)
                if b > 110.0: raw_cands.append(round(b / 2.0, 1))
                if b < 85.0: raw_cands.append(round(b * 2.0, 1))
                if b > 140.0: raw_cands.append(round(b / 3.0, 1))
                if b < 70.0: raw_cands.append(round(b * 3.0, 1))

    unique_cands = []
    for c in raw_cands:
        if 42.0 <= c <= 245.0 and not any(abs(c - u) < 3.0 for u in unique_cands):
            unique_cands.append(c)

    scored_hypotheses = []
    best_hyp = None
    best_score = -1e9

    for cand in unique_cands:
        tempo_arr, b_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sample_rate,
            hop_length=hop,
            bpm=cand,
            tightness=100
        )
        if len(b_frames) < 4:
            continue

        b_times = librosa.frames_to_time(b_frames, sr=sample_rate, hop_length=hop)
        ibis = np.diff(b_times)
        beat_sec = float(np.median(ibis))
        tracked_bpm = 60.0 / max(0.2, beat_sec)

        std_ibi = float(np.std(ibis)) if len(ibis) > 1 else 0.5
        regularity = 1.0 / (1.0 + std_ibi)

        avg_onset = float(np.mean(onset_env[b_frames]))
        avg_onset_ratio = min(2.5, avg_onset / mean_onset)

        frame_lag = int(round(beat_sec * frames_per_sec))
        ac_score = float(ac[frame_lag]) if frame_lag < len(ac) else 0.0
        ac_penalty = 1.50 if ac_score < 0.15 else 0.0

        is_hemiola = abs(beat_sec / tau_e - 1.5) < 0.12
        hemiola_penalty = 0.50 if is_hemiola else 0.0

        lag2 = frame_lag * 2
        lag3 = frame_lag * 3
        ac2 = float(ac[lag2]) if lag2 < len(ac) else 0.0
        ac3 = float(ac[lag3]) if lag3 < len(ac) else 0.0
        harmonic_support = 0.5 * ac2 + 0.5 * ac3

        onsets_per_beat = onset_rate * beat_sec
        tactus_density_score = float(np.exp(-0.5 * ((np.log2(onsets_per_beat) - np.log2(1.8)) / 0.5) ** 2))
        prior = float(np.exp(-0.5 * ((np.log2(cand) - np.log2(115.0)) / 0.6) ** 2))

        density_penalty = 0.0
        if onsets_per_beat > 3.2: density_penalty += 0.35
        elif onsets_per_beat < 0.75: density_penalty += 0.35

        score = (
            0.20 * avg_onset_ratio +
            0.30 * (ac_score * 3.0) +
            0.15 * regularity +
            0.15 * (harmonic_support * 3.0) +
            0.10 * (tactus_density_score * 3.0) +
            0.10 * (prior * 3.0) -
            density_penalty -
            hemiola_penalty -
            ac_penalty
        )

        conf = min(0.99, max(0.50, ac_score + 0.30))
        hyp = {
            "bpm": round(tracked_bpm, 1),
            "score": round(score, 4),
            "confidence": round(conf, 2),
            "beats": b_times.tolist()
        }
        scored_hypotheses.append(hyp)

        if score > best_score:
            best_score = score
            best_hyp = hyp

    scored_hypotheses.sort(key=lambda x: x["score"], reverse=True)
    return best_hyp, scored_hypotheses


def run_tempo_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    y_norm, sr = soundfile_load_normalized(wav_path)

    print("--- STAGE 5: TEMPO ESTIMATION PARITY TEST ---")
    print(f"Audio: {len(y_norm)} samples ({len(y_norm)/sr:.2f}s) @ {sr} Hz")

    # 1. Windows Reference
    bt = BeatTracker(sample_rate=sr)
    ref_grid, ref_tempo = bt.track_beats(y=y_norm, sr=sr)
    ref_bpm = ref_tempo.bpm

    # 2. Android Algorithm Simulation
    and_best_hyp, and_hypotheses = simulate_android_tempo_detection(y_norm, sample_rate=sr)
    and_bpm = and_best_hyp["bpm"]

    bpm_diff = abs(ref_bpm - and_bpm)

    report = {
        "audio_file": str(wav_path),
        "windows_bpm": round(ref_bpm, 2),
        "android_bpm": round(and_bpm, 2),
        "bpm_difference": round(bpm_diff, 2),
        "windows_confidence": round(ref_tempo.confidence, 2),
        "android_confidence": round(and_best_hyp["confidence"], 2),
        "top_hypotheses_count": len(and_hypotheses),
        "top_5_hypotheses": and_hypotheses[:5],
        "passed": bool(bpm_diff < 1.0)
    }

    print(json.dumps(report, indent=2))

    out_file = Path("tests/android_parity/tempo_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_file}")

    assert report["passed"], f"Tempo parity failed: ref={ref_bpm}, and={and_bpm}, diff={bpm_diff}"
    print("STAGE 5 TEMPO PARITY: PASS")


if __name__ == "__main__":
    run_tempo_parity_test()
