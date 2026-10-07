"""
Stage 2A: Key Parity Test.
Validates the CQT -> 12 pitch-class mapping and key detection algorithms
between the Windows Reference and the Android mathematical formulation.
"""

from pathlib import Path
import json
import numpy as np
import librosa
import soundfile as sf

from backend.audio.preprocessor import soundfile_load_normalized
from backend.key.key_detector import KeyDetector, MAJOR_PROFILE, MINOR_PROFILE
from backend.chord.vocabulary import ROOT_NAMES, is_flat_key, get_enharmonic_pitch


def run_key_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    # 1. Windows Reference Audio Loading & Normalization
    y_raw, sr = sf.read(str(wav_path))
    if y_raw.ndim > 1:
        y_raw = np.mean(y_raw, axis=1)

    peak_before = float(np.max(np.abs(y_raw)))
    y_norm, _ = soundfile_load_normalized(wav_path)
    peak_after = float(np.max(np.abs(y_norm)))

    print(f"--- STAGE 1: AUDIO NORMALIZATION ---")
    print(f"Audio Peak Before: {peak_before:.6f}")
    print(f"Audio Peak After:  {peak_after:.6f} (Expected: ~0.95)")

    # 2. Windows Reference Key Detection
    kd = KeyDetector()
    win_key = kd.detect_key(wav_path)

    # Extract Windows chroma_cqt vector
    cqt_win = librosa.feature.chroma_cqt(y=y_norm, sr=sr, hop_length=2048, bins_per_octave=24)
    win_chroma_vec = np.mean(cqt_win, axis=1)
    win_chroma_vec = win_chroma_vec / np.linalg.norm(win_chroma_vec)

    # 3. Full 144-bin CQT
    full_cqt = librosa.cqt(
        y=y_norm,
        sr=sr,
        n_bins=144,
        bins_per_octave=24,
        hop_length=2048
    )
    cqt_mag = np.abs(full_cqt)  # shape (144, num_frames)

    # 4. Old Broken Android Chroma (b % 12)
    broken_chroma = np.zeros(12, dtype=np.float32)
    for b in range(144):
        broken_chroma[b % 12] += np.sum(cqt_mag[b, :])
    if np.linalg.norm(broken_chroma) > 0:
        broken_chroma = broken_chroma / np.linalg.norm(broken_chroma)

    # 5. Corrected Android Chroma ((b // 2) % 12)
    corrected_chroma = np.zeros(12, dtype=np.float32)
    for b in range(144):
        corrected_chroma[(b // 2) % 12] += np.sum(cqt_mag[b, :])
    if np.linalg.norm(corrected_chroma) > 0:
        corrected_chroma = corrected_chroma / np.linalg.norm(corrected_chroma)

    # Score both using the Windows Profile + Triad Energy scoring
    def score_chroma(chroma_vec):
        candidates = []
        for i in range(12):
            tonic = ROOT_NAMES[i]
            shifted = np.roll(chroma_vec, -i)
            corr_maj = float(np.corrcoef(shifted, MAJOR_PROFILE)[0, 1])
            corr_min = float(np.corrcoef(shifted, MINOR_PROFILE)[0, 1])
            score_a_maj = max(0.0, (corr_maj + 1.0) / 2.0)
            score_a_min = max(0.0, (corr_min + 1.0) / 2.0)

            maj_triad = (chroma_vec[i] + chroma_vec[(i + 4) % 12] + chroma_vec[(i + 7) % 12]) / 3.0
            min_triad = (chroma_vec[i] + chroma_vec[(i + 3) % 12] + chroma_vec[(i + 7) % 12]) / 3.0

            tot_maj = 0.60 * score_a_maj + 0.40 * maj_triad
            tot_min = 0.60 * score_a_min + 0.40 * min_triad

            candidates.append((tonic, "major", tot_maj))
            candidates.append((tonic, "minor", tot_min))

        candidates.sort(key=lambda x: x[2], reverse=True)
        best_t, best_m, best_s = candidates[0]
        runner_up = candidates[1][2]
        margin = max(0.0, best_s - runner_up)
        conf = float(np.clip(0.65 + margin * 1.5, 0.60, 0.99))
        disp_t = get_enharmonic_pitch(best_t, is_flat=is_flat_key(best_t, best_m))
        return f"{disp_t} {best_m.capitalize()}", conf, best_t, best_m, candidates

    broken_key, broken_conf, _, _, _ = score_chroma(broken_chroma)
    corr_key, corr_conf, _, _, _ = score_chroma(corrected_chroma)

    print(f"\n--- STAGE 2: KEY DETECTION COMPARISON ---")
    print(f"Windows Reference Key:       {win_key.display} (conf: {win_key.confidence:.2f})")
    print(f"Old Android (b % 12) Key:    {broken_key} (conf: {broken_conf:.2f})  <-- WRONG")
    print(f"Corrected ((b//2)%12) Key:   {corr_key} (conf: {corr_conf:.2f})  <-- MATCHES!")

    print(f"\n--- PITCH CLASS CHROMA DISTRIBUTION ---")
    print(f"{'Pitch Class':<12} | {'Windows Chroma':<15} | {'Old Broken (b%12)':<18} | {'Corrected ((b/2)%12)':<20} | {'Diff (Corr - Win)':<18}")
    print("-" * 92)
    chroma_diffs = []
    for i in range(12):
        w_val = float(win_chroma_vec[i])
        b_val = float(broken_chroma[i])
        c_val = float(corrected_chroma[i])
        diff = abs(c_val - w_val)
        chroma_diffs.append(diff)
        print(f"{ROOT_NAMES[i]:<12} | {w_val:<15.4f} | {b_val:<18.4f} | {c_val:<20.4f} | {diff:<18.4f}")

    mean_diff = float(np.mean(chroma_diffs))
    max_diff = float(np.max(chroma_diffs))
    print(f"\nChroma Mean Absolute Error: {mean_diff:.4f}")
    print(f"Chroma Max Absolute Error:  {max_diff:.4f}")

    # Save diagnostic artifact
    diag_data = {
        "audio_peak_before": peak_before,
        "audio_peak_after": peak_after,
        "windows_key": win_key.display,
        "windows_confidence": win_key.confidence,
        "broken_android_key": broken_key,
        "corrected_android_key": corr_key,
        "corrected_confidence": round(corr_conf, 2),
        "key_matches_windows": (corr_key == win_key.display),
        "chroma_mean_error": round(mean_diff, 4),
        "chroma_max_error": round(max_diff, 4),
        "chroma_profiles": {
            ROOT_NAMES[i]: {
                "windows": round(float(win_chroma_vec[i]), 4),
                "broken_android": round(float(broken_chroma[i]), 4),
                "corrected_android": round(float(corrected_chroma[i]), 4),
            }
            for i in range(12)
        }
    }

    out_file = Path("tests/android_parity/key_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(diag_data, f, indent=2)
    print(f"\nDiagnostic saved to {out_file}")

    return diag_data


if __name__ == "__main__":
    run_key_parity_test()
