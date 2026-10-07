"""
Stage 6: Dynamic Programming Beat Tracking Parity Test.
Compares the Windows reference librosa.beat.beat_track against the Android EllisBeatTracker engine.
Verifies that beats follow real onsets (starting at ~5.25s) with exact temporal alignment (<10ms MAE).
"""

from pathlib import Path
import json
import numpy as np
import librosa
import soundfile as sf

from backend.audio.preprocessor import soundfile_load_normalized
from backend.beat.beat_tracker import BeatTracker
from tests.android_parity.test_onset_parity import compute_android_spectral_flux_onset


def simulate_android_ellis_dp_beat_track(onset_env, bpm=86.1, sample_rate=22050, hop_length=512, tightness=100.0, trim=True):
    n = len(onset_env)
    frame_rate = float(sample_rate) / hop_length
    frames_per_beat = float(round(frame_rate * 60.0 / bpm))

    # 1. Normalize onsets by standard deviation
    std = float(np.std(onset_env, ddof=1))
    norm_env = onset_env / (std + 1e-12)

    # 2. Local score smoothing with Gaussian window
    fpb_int = int(frames_per_beat)
    k_len = 2 * fpb_int + 1
    k_arr = np.arange(-fpb_int, fpb_int + 1)
    win = np.exp(-0.5 * (k_arr * 32.0 / frames_per_beat) ** 2)

    local_score = np.zeros(n, dtype=np.float32)
    for i in range(n):
        k_min = max(0, i + k_len // 2 - n + 1)
        k_max = min(i + k_len // 2, k_len - 1)
        s = 0.0
        for k in range(k_min, k_max + 1):
            s += win[k] * norm_env[i + k_len // 2 - k]
        local_score[i] = s

    # 3. Dynamic programming
    cum_score = np.zeros(n, dtype=np.float64)
    backlink = np.full(n, -1, dtype=np.int32)
    max_local = float(np.max(local_score))
    score_thresh = 0.01 * max_local
    first_beat = True
    cum_score[0] = local_score[0]

    ln_fpb = np.log(frames_per_beat)
    half_fpb = int(round(frames_per_beat / 2.0))
    two_fpb = int(2.0 * frames_per_beat)

    for i in range(n):
        best_score = -1e18
        beat_loc = -1
        start_loc = i - half_fpb
        end_loc = i - two_fpb

        for loc in range(start_loc, end_loc - 1, -1):
            if loc < 0:
                break
            diff = float(i - loc)
            penalty = tightness * ((np.log(diff) - ln_fpb) ** 2)
            sc = cum_score[loc] - penalty
            if sc > best_score:
                best_score = sc
                beat_loc = loc

        cum_score[i] = local_score[i] + (best_score if beat_loc >= 0 else 0.0)

        if first_beat and local_score[i] < score_thresh:
            backlink[i] = -1
        else:
            backlink[i] = beat_loc
            first_beat = False

    # 4. Find last beat: local maxima thresholded by 0.5 * median(local maxima)
    local_maxima = []
    for i in range(1, n - 1):
        if cum_score[i] > cum_score[i - 1] and cum_score[i] >= cum_score[i + 1]:
            local_maxima.append(cum_score[i])

    med = np.median(local_maxima) if local_maxima else cum_score[-1]
    median_thresh = 0.5 * med

    tail = n - 1
    for i in range(n - 1, -1, -1):
        is_max = (i > 0 and i < n - 1 and cum_score[i] > cum_score[i - 1] and cum_score[i] >= cum_score[i + 1])
        if is_max and cum_score[i] >= median_thresh:
            tail = i
            break

    # 5. Backtrack
    beat_frames = []
    curr = tail
    while curr >= 0:
        beat_frames.append(curr)
        curr = backlink[curr]
    beat_frames.reverse()

    # 6. Trim leading/trailing weak onsets
    if trim and len(beat_frames) > 0:
        w = np.hanning(5)
        num_beats = len(beat_frames)
        smooth_boe = np.convolve(local_score[beat_frames], w)[2 : num_beats + 2]
        trim_thresh = 0.5 * np.sqrt(np.mean(smooth_boe ** 2))

        min_frame = 0
        while min_frame < n and local_score[min_frame] <= trim_thresh:
            min_frame += 1

        max_frame = n - 1
        while max_frame >= 0 and local_score[max_frame] <= trim_thresh:
            max_frame -= 1

        beat_frames = [f for f in beat_frames if min_frame <= f <= max_frame]

    frame_to_time = float(hop_length) / sample_rate
    return [round(f * frame_to_time, 4) for f in beat_frames]


def run_beat_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    y_norm, sr = soundfile_load_normalized(wav_path)

    print("--- STAGE 6: BEAT TRACKING PARITY TEST ---")
    print(f"Audio: {len(y_norm)} samples ({len(y_norm)/sr:.2f}s) @ {sr} Hz")

    # 1. Windows Reference
    bt = BeatTracker(sample_rate=sr)
    ref_grid, ref_tempo = bt.track_beats(y=y_norm, sr=sr)
    ref_beats = [round(b, 4) for b in ref_grid.beats]

    # 2. Android Algorithm Simulation
    onset_env = compute_android_spectral_flux_onset(y_norm, sample_rate=sr)
    and_beats = simulate_android_ellis_dp_beat_track(onset_env, bpm=ref_tempo.bpm, sample_rate=sr, hop_length=512)

    min_len = min(len(ref_beats), len(and_beats))
    time_diffs = [abs(ref_beats[i] - and_beats[i]) for i in range(min_len)]
    mae_beats = float(np.mean(time_diffs))
    max_diff_beats = float(np.max(time_diffs))

    first_beat_ref = ref_beats[0] if ref_beats else 0.0
    first_beat_and = and_beats[0] if and_beats else 0.0
    first_beat_diff = abs(first_beat_ref - first_beat_and)

    report = {
        "audio_file": str(wav_path),
        "bpm": ref_tempo.bpm,
        "windows_beat_count": len(ref_beats),
        "android_beat_count": len(and_beats),
        "count_difference": len(ref_beats) - len(and_beats),
        "windows_first_5_beats": ref_beats[:5],
        "android_first_5_beats": and_beats[:5],
        "windows_first_beat_sec": first_beat_ref,
        "android_first_beat_sec": first_beat_and,
        "first_beat_diff_seconds": round(first_beat_diff, 4),
        "mean_absolute_error_seconds": round(mae_beats, 5),
        "max_absolute_error_seconds": round(max_diff_beats, 5),
        "passed": bool(len(ref_beats) == len(and_beats) and mae_beats < 0.010 and first_beat_diff < 0.010)
    }

    print(json.dumps(report, indent=2))

    out_file = Path("tests/android_parity/beat_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_file}")

    assert report["passed"], f"Beat tracking parity failed: diff={len(ref_beats) - len(and_beats)}, mae={mae_beats}"
    print("STAGE 6 BEAT TRACKING PARITY: PASS")


if __name__ == "__main__":
    run_beat_parity_test()
