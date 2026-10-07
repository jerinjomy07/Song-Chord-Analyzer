"""
Stage 7: Downbeat Phase & Meter Detection Parity Test.
Compares the Windows reference MeterDetector against the Android downbeat and meter detection engine.
Verifies time signature (4/4), downbeat count (89), downbeat timestamps, and phase on the golden song Bekhayali.
"""

from pathlib import Path
import json
import numpy as np
import soundfile as sf
import librosa
from scipy.signal import butter, sosfilt

from backend.audio.preprocessor import soundfile_load_normalized
from backend.beat.beat_tracker import BeatTracker
from backend.meter.meter_detector import MeterDetector
from tests.android_parity.test_beat_parity import simulate_android_ellis_dp_beat_track
from tests.android_parity.test_onset_parity import compute_android_spectral_flux_onset


def simulate_android_downbeat_and_meter(audio, sample_rate=22050):
    hop = 512
    frames_per_sec = float(sample_rate) / hop
    onset_env = compute_android_spectral_flux_onset(audio, sample_rate)
    n_frames = len(onset_env)

    # Autocorrelation of onset envelope
    max_lag = min(n_frames - 1, int(5.5 * frames_per_sec))
    ac_full = np.correlate(onset_env, onset_env, mode='full')
    ac = ac_full[n_frames - 1 : n_frames - 1 + max_lag]
    ac = ac / (ac[0] + 1e-8)

    # Subdivision pulse tau_e
    sub_peaks = []
    for lag in range(2, max_lag - 2):
        t = lag / frames_per_sec
        if 0.16 <= t <= 0.46 and ac[lag] > ac[lag - 1] and ac[lag] > ac[lag + 1]:
            sub_peaks.append((t, float(ac[lag])))
    sub_peaks.sort(key=lambda x: x[1], reverse=True)
    tau_e = sub_peaks[0][0] if sub_peaks else 0.35

    # Onsets & tactus
    onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sample_rate, hop_length=hop, units='time')
    duration = len(audio) / sample_rate
    onset_rate = len(onsets) / max(1.0, duration)
    mean_onset = float(np.mean(onset_env)) + 1e-8

    min_lag = max(4, int(frames_per_sec * 60.0 / 250.0))
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

    unique_cands = []
    for c in raw_cands:
        if 42.0 <= c <= 245.0 and not any(abs(c - u) < 3.0 for u in unique_cands):
            unique_cands.append(c)

    scored_hypotheses = []
    best_hyp = None
    best_score = -1e9

    for cand in unique_cands:
        b_times = simulate_android_ellis_dp_beat_track(onset_env, bpm=cand, sample_rate=sample_rate, hop_length=hop)
        if len(b_times) < 4:
            continue

        ibis = np.diff(b_times)
        beat_sec = float(np.median(ibis))
        tracked_bpm = 60.0 / max(0.2, beat_sec)

        std_ibi = float(np.std(ibis)) if len(ibis) > 1 else 0.5
        regularity = 1.0 / (1.0 + std_ibi)

        b_frames = [int(round(t * frames_per_sec)) for t in b_times]
        b_frames = np.clip(b_frames, 0, n_frames - 1)
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
            "beats": b_times
        }
        scored_hypotheses.append(hyp)

        if score > best_score:
            best_score = score
            best_hyp = hyp

    detected_bpm = best_hyp["bpm"]
    beats = best_hyp["beats"]

    # Multi-Meter & Downbeat Phase
    meter_candidates = [
        (2, 4, "2/4"),
        (3, 4, "3/4"),
        (4, 4, "4/4"),
        (6, 8, "6/8"),
        (7, 8, "7/8"),
        (12, 8, "12/8")
    ]

    beat_sec = 60.0 / max(30.0, detected_bpm)
    idx_half = int(round((beat_sec / 2.0) * frames_per_sec))
    idx_third = int(round((beat_sec / 3.0) * frames_per_sec))
    ac_half = float(ac[idx_half]) if idx_half < len(ac) else 0.0
    ac_third = float(ac[idx_third]) if idx_third < len(ac) else 0.0
    is_ternary = (detected_bpm <= 100.0 and ac_third > 0.20 and ac_third > ac_half * 1.05)

    templates = {
        "2/4": np.array([1.0, 0.40]),
        "3/4": np.array([1.0, 0.35, 0.45]),
        "4/4": np.array([1.0, 0.30, 0.70, 0.30]),
        "6/8": np.array([1.0, 0.40]),
        "7/8": np.array([1.0, 0.20, 0.80, 0.20, 0.80, 0.20, 0.20]),
        "12/8": np.array([1.0, 0.30, 0.70, 0.30])
    }

    # Lowpass 130Hz filter for bass energy
    sos = butter(4, 130, 'lowpass', fs=sample_rate, output='sos')
    rms_low = librosa.feature.rms(y=sosfilt(sos, audio), hop_length=hop)[0]

    b_frames = [int(round(t * frames_per_sec)) for t in beats]
    b_frames = np.clip(b_frames, 0, n_frames - 1)
    b_onset = onset_env[b_frames]
    b_onset = (b_onset - np.mean(b_onset)) / (np.std(b_onset) + 1e-6)
    b_bass = rms_low[b_frames]
    b_bass = (b_bass - np.mean(b_bass)) / (np.std(b_bass) + 1e-6)

    beat_salience = 0.55 * b_onset + 0.45 * b_bass

    # Autocorrelation of beat salience
    ac_sal = np.correlate(beat_salience, beat_salience, mode='full')
    half_s = len(ac_sal) // 2
    lags = ac_sal[half_s : half_s + 16] / (ac_sal[half_s] + 1e-8)

    meter_scores = {}
    best_meter = (4, 4, "4/4")
    best_meter_score = -1e9
    best_phase = 0
    best_k = 4

    for num, den, tag in meter_candidates:
        k = 2 if (den == 8 and num == 6) else (4 if (den == 8 and num == 12) else (7 if den == 8 else num))
        if k >= len(lags):
            continue

        periodicity = float(lags[k])
        num_bars = len(beat_salience) // k
        if num_bars < 2:
            continue

        folded = np.mean([beat_salience[i * k : (i + 1) * k] for i in range(num_bars)], axis=0)
        tmpl = templates.get(tag, np.ones(k))

        best_phi_score = -1e9
        phi_for_meter = 0

        for phi in range(k):
            rolled = np.roll(folded, -phi)
            corr = float(np.corrcoef(rolled, tmpl)[0, 1]) if np.std(rolled) > 1e-6 else 0.0
            down_e = max(0.0, float(folded[phi]))
            ps = 0.50 * corr + 0.50 * down_e
            if ps > best_phi_score:
                best_phi_score = ps
                phi_for_meter = phi

        contrast = periodicity
        if k == 3: contrast = periodicity - max(float(lags[2]), float(lags[4]))
        elif k == 2: contrast = periodicity - float(lags[1])
        elif k == 4: contrast = periodicity - float(lags[3])
        elif k == 7: contrast = periodicity - float(lags[6])

        phrase_pen = 0.0
        if k == 4 and lags[2] > 0.35 and lags[2] >= lags[4] * 0.98 and not is_ternary:
            phrase_pen = 0.25
        elif k == 4 and is_ternary and lags[2] > 0.40 and lags[2] > lags[4] * 1.05:
            phrase_pen = 0.20

        prior = float(np.exp(-0.5 * ((np.log2(detected_bpm) - np.log2(60.0 if is_ternary else 110.0)) / 0.6) ** 2))
        total_score = 0.35 * periodicity + 0.25 * contrast + 0.20 * best_phi_score + 0.10 * prior - phrase_pen
        meter_scores[tag] = total_score

        if total_score > best_meter_score:
            best_meter_score = total_score
            best_meter = (num, den, tag)
            best_phase = phi_for_meter
            best_k = k

    downbeats = [beats[i] for i in range(best_phase, len(beats), best_k)]
    return best_meter[2], detected_bpm, downbeats, best_phase, meter_scores


def run_downbeat_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    y_norm, sr = soundfile_load_normalized(wav_path)

    print("--- STAGE 7: DOWNBEAT & METER PARITY TEST ---")
    print(f"Audio: {len(y_norm)} samples ({len(y_norm)/sr:.2f}s) @ {sr} Hz")

    # 1. Windows Reference
    bt = BeatTracker(sample_rate=sr)
    ref_grid, ref_tempo = bt.track_beats(y=y_norm, sr=sr)
    md = MeterDetector(sample_rate=sr)
    ref_meter_res = md.detect_meter(y=y_norm, sr=sr, beat_times=ref_grid.beats, bpm=ref_tempo.bpm, tempo_info=ref_tempo)
    ref_meter = ref_meter_res.display
    ref_downbeats = [round(b, 4) for b in ref_meter_res.downbeats]

    # 2. Android Algorithm Simulation
    and_meter, and_bpm, and_downbeats, and_phase, and_scores = simulate_android_downbeat_and_meter(y_norm, sample_rate=sr)

    min_len = min(len(ref_downbeats), len(and_downbeats))
    time_diffs = [abs(ref_downbeats[i] - and_downbeats[i]) for i in range(min_len)]
    mae_downbeats = float(np.mean(time_diffs))
    max_diff_downbeats = float(np.max(time_diffs))

    first_db_ref = ref_downbeats[0] if ref_downbeats else 0.0
    first_db_and = and_downbeats[0] if and_downbeats else 0.0
    first_db_diff = abs(first_db_ref - first_db_and)

    report = {
        "audio_file": str(wav_path),
        "windows_meter": ref_meter,
        "android_meter": and_meter,
        "windows_downbeat_count": len(ref_downbeats),
        "android_downbeat_count": len(and_downbeats),
        "count_difference": len(ref_downbeats) - len(and_downbeats),
        "windows_first_5_downbeats": ref_downbeats[:5],
        "android_first_5_downbeats": and_downbeats[:5],
        "windows_first_downbeat_sec": first_db_ref,
        "android_first_downbeat_sec": first_db_and,
        "first_downbeat_diff_seconds": round(first_db_diff, 4),
        "mean_absolute_error_seconds": round(mae_downbeats, 5),
        "max_absolute_error_seconds": round(max_diff_downbeats, 5),
        "passed": bool(ref_meter == and_meter and len(ref_downbeats) == len(and_downbeats) and mae_downbeats < 0.010 and first_db_diff < 0.010)
    }

    print(json.dumps(report, indent=2))

    out_file = Path("tests/android_parity/downbeat_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_file}")

    assert report["passed"], f"Downbeat parity failed: meter={and_meter}, diff={len(ref_downbeats) - len(and_downbeats)}, mae={mae_downbeats}"
    print("STAGE 7 DOWNBEAT & METER PARITY: PASS")


if __name__ == "__main__":
    run_downbeat_parity_test()
