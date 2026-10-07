"""
Stage 3: CQT Parity Diagnostic.
Compares the Windows reference librosa.cqt against the Android decimation filter bank CQT.
Evaluates frame counts, numerical precision, shape, MAE, Max Error, and frame alignment.
"""

from pathlib import Path
import json
import numpy as np
import librosa
import soundfile as sf

from backend.audio.preprocessor import soundfile_load_normalized


def decimate2_fir(x):
    """Exact 15-tap halfband FIR anti-aliasing decimation filter matching Android CqtExtractor.kt."""
    h = np.array([
        -0.0034, 0.0, 0.0211, 0.0, -0.0768, 0.0, 0.3091, 0.5000,
        0.3091, 0.0, -0.0768, 0.0, 0.0211, 0.0, -0.0034
    ], dtype=np.float32)
    
    pad_h = len(h) // 2
    x_padded = np.pad(x, (pad_h, pad_h), mode='constant')
    out_len = len(x) // 2
    # Convolve at stride 2
    out = np.zeros(out_len, dtype=np.float32)
    for i in range(out_len):
        out[i] = np.sum(x_padded[2 * i : 2 * i + len(h)] * h)
    return out


def run_cqt_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    y_norm, sr = soundfile_load_normalized(wav_path)
    # Take an exact 20-second excerpt for high-precision frame comparison
    duration_test = 20.0
    num_samples = int(duration_test * sr)
    y_test = y_norm[:num_samples]

    print(f"--- STAGE 3: CQT PARITY DIAGNOSTIC ---")
    print(f"Test Excerpt: {len(y_test)} samples ({len(y_test)/sr:.2f}s) @ {sr} Hz")

    # 1. Windows Reference CQT
    cqt_win = librosa.cqt(
        y_test,
        sr=sr,
        n_bins=144,
        bins_per_octave=24,
        hop_length=2048
    )
    cqt_win_mag = np.abs(cqt_win) # shape (144, num_frames)

    MEAN = -2.2279878897355596
    STD = 1.7191329394436938
    feat_win = (np.log(cqt_win_mag + 1e-6).T - MEAN) / STD # (num_frames, 144)

    # 2. Android Algorithm Simulation
    from backend.chord.vocabulary import ROOT_NAMES
    # Compute librosa reference basis to verify exact Android basis weights
    alpha = librosa.filters._relative_bandwidth(freqs=librosa.cqt_frequencies(n_bins=144, fmin=librosa.note_to_hz('C1'), bins_per_octave=24))
    lengths, _ = librosa.filters.wavelet_lengths(
        freqs=librosa.cqt_frequencies(n_bins=144, fmin=librosa.note_to_hz('C1'), bins_per_octave=24),
        sr=sr,
        window='hann',
        filter_scale=1,
        gamma=0,
        alpha=alpha
    )

    # Android Octave Decimation Engine
    # Early downsampling
    y_early = decimate2_fir(y_test) * np.sqrt(2.0)
    current_y = y_early.copy()
    current_hop = 1024

    n_fft = 512
    pad_len = n_fft // 2

    octave_responses = []

    # Get top octave basis from librosa for exact reference
    fft_basis_top, _, _ = librosa.core.constantq.__vqt_filter_fft(
        sr=11025,
        freqs=librosa.cqt_frequencies(n_bins=144, fmin=librosa.note_to_hz('C1'), bins_per_octave=24)[-24:],
        filter_scale=1.0,
        norm=1,
        sparsity=0.01,
        window='hann',
        gamma=0.0,
        dtype=np.complex64,
        alpha=librosa.core.constantq.__et_relative_bw(24)
    )

    for oct_idx in range(6):
        oct_scale = np.sqrt(2.0 ** (oct_idx + 1))
        # STFT with window='ones' (embedded window in basis) and padding n_fft // 2
        padded_y = np.pad(current_y, (pad_len, pad_len), mode='constant')
        n_frames = max(1, (len(padded_y) - n_fft) // current_hop + 1)

        oct_mat = np.zeros((24, n_frames), dtype=np.complex64)
        for f in range(n_frames):
            frame = padded_y[f * current_hop : f * current_hop + n_fft]
            X = np.fft.rfft(frame, n=n_fft)
            oct_mat[:, f] = fft_basis_top.dot(X) * oct_scale

        octave_responses.append(oct_mat)

        if oct_idx < 5:
            current_hop //= 2
            current_y = decimate2_fir(current_y) * np.sqrt(2.0)

    # Determine trim length: max_col = min across octaves
    min_frames = min(resp.shape[1] for resp in octave_responses)
    android_cqt_mag = np.zeros((144, min_frames), dtype=np.float32)

    for oct_idx in range(6):
        # oct_idx 0 is top octave (freqs 120..143)
        # oct_idx 5 is bottom octave (freqs 0..23)
        bin_start = 144 - (oct_idx + 1) * 24
        bin_end = bin_start + 24
        # Slice to min_frames
        oct_mag = np.abs(octave_responses[oct_idx][:, :min_frames])
        for b in range(24):
            global_b = bin_start + b
            android_cqt_mag[global_b, :] = oct_mag[b, :] / np.sqrt(lengths[global_b])

    feat_android = (np.log(android_cqt_mag + 1e-6).T - MEAN) / STD

    # Numerical Comparison
    common_frames = min(feat_win.shape[0], feat_android.shape[0])
    frame_diff = abs(feat_win.shape[0] - feat_android.shape[0])

    diff_matrix = np.abs(feat_win[:common_frames, :] - feat_android[:common_frames, :])
    mae = float(np.mean(diff_matrix))
    max_err = float(np.max(diff_matrix))
    corr = float(np.corrcoef(feat_win[:common_frames, :].flatten(), feat_android[:common_frames, :].flatten())[0, 1])

    print(f"Windows Feature Shape:  {feat_win.shape}")
    print(f"Android Feature Shape:  {feat_android.shape}")
    print(f"Frame Alignment Diff:   {frame_diff} frames (out of {feat_win.shape[0]})")
    print(f"Mean Absolute Error:    {mae:.5f}")
    print(f"Max Absolute Error:     {max_err:.5f}")
    print(f"Correlation:            {corr:.5f} (Target > 0.98)")

    diag_data = {
        "windows_shape": list(feat_win.shape),
        "android_shape": list(feat_android.shape),
        "frame_alignment_error": frame_diff,
        "mean_absolute_error": round(mae, 5),
        "max_absolute_error": round(max_err, 5),
        "feature_correlation": round(corr, 5),
        "parity_acceptable": bool(mae < 0.08 and corr > 0.98)
    }

    out_file = Path("tests/android_parity/cqt_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(diag_data, f, indent=2)
    print(f"Diagnostic saved to {out_file}")

    return diag_data


if __name__ == "__main__":
    run_cqt_parity_test()
