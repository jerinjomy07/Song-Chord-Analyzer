"""
Multi-song evaluation benchmark: Evaluates cross-song musical parity
between Windows Reference Pipeline and Android Candidate ONNX Engine across different genres.
"""

from pathlib import Path
import sys
import json
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import soundfile as sf
import librosa
from scipy.signal import butter, sosfilt
import onnxruntime as ort

from backend.pipeline import SongAnalyzerPipeline
from scripts.verify_windows_android_parity import AndroidCandidateEngine, compute_parity_metrics

def benchmark_song(audio_path: Path, song_name: str, duration_sec: float = 60.0):
    print(f"\n============================================================")
    print(f"BENCHMARKING MULTI-SONG TRACK: {song_name}")
    print(f"============================================================")

    # Prepare temporary excerpt if audio is very long
    y, sr = sf.read(str(audio_path))
    if y.ndim > 1: y = np.mean(y, axis=1)
    max_samples = int(duration_sec * sr)
    if len(y) > max_samples:
        y_clip = y[:max_samples]
    else:
        y_clip = y
    
    temp_clip_path = ROOT / "storage" / "temp" / f"eval_clip_{song_name.split()[0]}.wav"
    temp_clip_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(temp_clip_path), y_clip, sr)

    onnx_path = ROOT / "mobile" / "android" / "native" / "inference" / "btc_model_170voca.onnx"
    and_engine = AndroidCandidateEngine(onnx_path)

    # 1. Android Candidate
    t0 = time.time()
    and_result = and_engine.analyze(temp_clip_path, song_title=song_name)
    and_time = time.time() - t0

    # 2. Windows Reference (Acoustic Mix Input - Identical Feature Conditions)
    pipeline = SongAnalyzerPipeline()
    t0 = time.time()
    win_result = pipeline.process(temp_clip_path, song_title=song_name, enable_separation=False).model_dump()
    win_time = time.time() - t0

    # 3. Compute Metrics
    metrics = compute_parity_metrics(win_result, and_result)

    print(f"Track: {song_name} ({len(y_clip)/sr:.1f}s)")
    print(f"  Windows Analysis Time: {win_time:.2f}s | Android Analysis Time: {and_time:.2f}s")
    print(f"  Root Accuracy:        {metrics['root_accuracy_pct']}%")
    print(f"  Quality Accuracy:     {metrics['quality_accuracy_pct']}%")
    print(f"  Full Chord Match:     {metrics['full_chord_accuracy_pct']}%")
    print(f"  Timing Error:         {metrics['mean_timing_error_sec']}s")
    print(f"  Key Match:            {metrics['key_match']} ({metrics['windows_key']} vs {metrics['android_key']})")
    print(f"  BPM Error:            {metrics['bpm_error']} BPM")

    # Cleanup temp clip
    try:
        temp_clip_path.unlink()
    except Exception:
        pass

    return {
        "song_name": song_name,
        "duration_sec": round(len(y_clip)/sr, 1),
        "windows_time_sec": round(win_time, 2),
        "android_time_sec": round(and_time, 2),
        "metrics": metrics
    }

def main():
    uploads_dir = Path(r"C:\Users\jerin\AppData\Local\SongChordAnalyzer\uploads")
    
    # Locate files by prefix to avoid unicode fullwidth vertical bar issues
    carol_path = None
    radhimaa_path = None
    ray_path = None

    if uploads_dir.exists():
        for p in uploads_dir.iterdir():
            if p.name.startswith("6a90282f"):
                carol_path = p
            elif p.name.startswith("01f4da2c"):
                radhimaa_path = p
            elif p.name.startswith("bdf55774"):
                ray_path = p

    tracks = [
        ("Golden Parity (Multi-Instrumental)", ROOT / "storage" / "cache" / "ecdbc4dd2a6d827b_22k_mono.wav", 120.0),
        ("Carol Song (Malayalam Choral)", carol_path, 45.0),
        ("Radhimaa (Tamil Pop)", radhimaa_path, 45.0),
        ("Ray (Indie / Cinematic)", ray_path, 45.0)
    ]

    all_results = []
    for name, path, dur in tracks:
        if path and path.exists():
            res = benchmark_song(path, name, duration_sec=dur)
            all_results.append(res)
        else:
            print(f"Skipping {name}: file not found")

    # Output multi-song benchmark json
    out_path = ROOT / "tests" / "golden_parity" / "multisong_benchmark_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)

    print("\n============================================================")
    print("MULTI-SONG BENCHMARK SUMMARY TABLE")
    print("============================================================")
    print(f"{'Song Name':<38} | {'Root':<7} | {'Quality':<7} | {'Full':<7} | {'Key':<10} | {'Timing':<6}")
    print("-" * 85)
    for r in all_results:
        m = r["metrics"]
        print(f"{r['song_name']:<38} | {m['root_accuracy_pct']:>6}% | {m['quality_accuracy_pct']:>6}% | {m['full_chord_accuracy_pct']:>6}% | {str(m['key_match']):<10} | {m['mean_timing_error_sec']:>5}s")
    print("============================================================")

if __name__ == "__main__":
    main()
