"""
Stage 4: Spectral-Flux Onset Envelope Parity Test.
Compares the Windows reference librosa.onset.onset_strength against the Android SpectralFluxOnset engine.
Evaluates frame alignment, MAE, Max Absolute Error, and Pearson Correlation.
"""

from pathlib import Path
import json
import numpy as np
import librosa
import soundfile as sf

from backend.audio.preprocessor import soundfile_load_normalized


def compute_android_spectral_flux_onset(audio, sample_rate=22050):
    n_fft = 2048
    hop = 512
    pad = n_fft // 2
    n_mels = 128

    if len(audio) < hop:
        return np.array([], dtype=np.float32)

    n_frames = 1 + len(audio) // hop
    padded_size = len(audio) + 2 * pad
    padded_audio = np.zeros(padded_size, dtype=np.float32)

    # Reflect padding matching Android / librosa
    for i in range(pad):
        src = min(1 + i, len(audio) - 1)
        padded_audio[pad - 1 - i] = audio[src]
    padded_audio[pad : pad + len(audio)] = audio
    for i in range(pad):
        src = max(0, len(audio) - 2 - i)
        padded_audio[pad + len(audio) + i] = audio[src]

    # Hann window
    window = librosa.filters.get_window('hann', n_fft)

    # 128-band Mel filterbank
    fb = librosa.filters.mel(sr=sample_rate, n_fft=n_fft, n_mels=n_mels, fmax=11025, htk=False, norm='slaney')

    # STFT and Mel projection
    mel_spec = np.zeros((n_mels, n_frames), dtype=np.float32)
    for f in range(n_frames):
        start = f * hop
        frame = padded_audio[start : start + n_fft] * window
        spec = np.fft.rfft(frame)
        power = (np.abs(spec) ** 2).astype(np.float32)
        mel_spec[:, f] = np.dot(fb, power)

    # power_to_db: amin=1e-10, top_db=80.0, ref=max
    max_val = np.max(mel_spec)
    amin = 1e-10
    top_db = 80.0
    ref_db = 10.0 * np.log10(max(amin, float(max_val)))
    log_mel = 10.0 * np.log10(np.maximum(amin, mel_spec)) - ref_db
    log_mel = np.maximum(log_mel, -top_db)

    # First-order positive difference along frames
    diff = np.diff(log_mel, axis=1)
    onset_diff = np.maximum(0.0, diff)
    onset_mean = np.mean(onset_diff, axis=0)

    # Pad leading 3 frames
    pad_width = 1 + n_fft // (2 * hop) # 3
    onset_env = np.pad(onset_mean, (pad_width, 0), mode='constant')
    return onset_env[:n_frames]


def run_onset_parity_test():
    wav_path = Path("storage/cache/ecdbc4dd2a6d827b_22k_mono.wav")
    assert wav_path.exists(), f"Audio file not found: {wav_path}"

    y_norm, sr = soundfile_load_normalized(wav_path)

    print("--- STAGE 4: ONSET ENVELOPE PARITY TEST ---")
    print(f"Audio: {len(y_norm)} samples ({len(y_norm)/sr:.2f}s) @ {sr} Hz")

    # 1. Windows Reference
    ref_onset = librosa.onset.onset_strength(y=y_norm, sr=sr, hop_length=512)

    # 2. Android Algorithm
    and_onset = compute_android_spectral_flux_onset(y_norm, sample_rate=sr)

    # 3. Metrics
    mae = float(np.mean(np.abs(ref_onset - and_onset)))
    max_err = float(np.max(np.abs(ref_onset - and_onset)))
    corr = float(np.corrcoef(ref_onset, and_onset)[0, 1])

    report = {
        "audio_file": str(wav_path),
        "duration_seconds": round(len(y_norm) / sr, 2),
        "windows_frames": int(len(ref_onset)),
        "android_frames": int(len(and_onset)),
        "frame_count_diff": int(len(ref_onset) - len(and_onset)),
        "mean_absolute_error": round(mae, 6),
        "max_absolute_error": round(max_err, 6),
        "pearson_correlation": round(corr, 6),
        "windows_mean": round(float(np.mean(ref_onset)), 4),
        "android_mean": round(float(np.mean(and_onset)), 4),
        "windows_max": round(float(np.max(ref_onset)), 4),
        "android_max": round(float(np.max(and_onset)), 4),
        "passed": bool(corr > 0.999 and mae < 0.005)
    }

    print(json.dumps(report, indent=2))

    out_file = Path("tests/android_parity/onset_parity_report.json")
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report to {out_file}")

    assert report["passed"], f"Onset parity failed: corr={corr}, mae={mae}"
    print("STAGE 4 ONSET PARITY: PASS")


if __name__ == "__main__":
    run_onset_parity_test()
