"""
Standalone Demucs audio stem separation engine.
Runs locally with PyTorch CUDA / MPS / CPU.
Supports isolated stem extraction (--only bass,other) with live progress reporting.
"""

import argparse
import json
import struct
import sys
import time
import wave
import os
import numpy as np


def emit(**kwargs):
    print(json.dumps(kwargs), flush=True)


def fail(message):
    emit(type="error", message=str(message))
    sys.exit(1)


def crash_message(e):
    msg = f"{e}"
    low = msg.lower()
    if "no kernel image" in low or "invalid device function" in low:
        return (
            "GPU engine incompatible with this GPU (compute capability not supported) - "
            "falling back to CPU processing"
        )
    return msg[:400] or e.__class__.__name__


def load_wav(path):
    try:
        with wave.open(path, "rb") as w:
            sr = w.getframerate()
            channels = w.getnchannels()
            width = w.getsampwidth()
            frames = w.readframes(w.getnframes())
    except Exception as e:
        fail(f"Cannot read WAV {path}: {e}")
    if width == 2:
        audio = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    elif width == 4:
        audio = np.frombuffer(frames, dtype="<f4").astype(np.float32)
    else:
        fail(f"Unsupported sample width {width}")
    if channels == 0:
        fail("Empty WAV")
    audio = audio.reshape(-1, channels).T
    return audio, sr


def save_wav_f32(path, data, sr):
    """Write 32-bit float WAV (fmt tag 3); values above 1.0 are preserved."""
    channels, _ = data.shape
    payload = data.T.astype("<f4").tobytes()
    block_align = channels * 4
    header = b"RIFF" + struct.pack("<I", 36 + len(payload)) + b"WAVE"
    header += b"fmt " + struct.pack(
        "<IHHIIHH", 16, 3, channels, sr, sr * block_align, block_align, 32
    )
    header += b"data" + struct.pack("<I", len(payload))
    with open(path, "wb") as f:
        f.write(header)
        f.write(payload)


def run_separation(
    input_path: str,
    out_dir: str,
    model_name: str = "htdemucs",
    device: str = "auto",
    shifts: int = 1,
    overlap: float = 0.25,
    only: str = "bass,other",
    progress_callback=None,
):
    import torch
    import types

    # torch>=2.6 defaults torch.load(weights_only=True)
    _torch_load = torch.load

    def _load_any(*a, **k):
        k.setdefault("weights_only", False)
        return _torch_load(*a, **k)

    torch.load = _load_any

    import demucs.apply as dapply

    raw_tqdm = dapply.tqdm
    is_module = not hasattr(raw_tqdm, "update")
    real_tqdm = raw_tqdm.tqdm if is_module else raw_tqdm

    leg_state = {"done": 0, "total": 0, "last": -1.0, "legs": 0}

    class ProgressTqdm(real_tqdm):
        def __init__(self, *a, **kw):
            super().__init__(*a, **kw)
            if self.total:
                leg_state["total"] = self.total

        def update(self, n=1):
            super().update(n)
            self._report(False)

        def close(self):
            self._report(True)
            if self.total and self.n >= self.total:
                leg_state["done"] += 1
            super().close()

        def _report(self, force):
            legs = leg_state["legs"]
            if not legs:
                return
            total = leg_state["total"] or self.total or 0
            if not total:
                return
            frac = min(1.0, max(0.0, self.n / total))
            now = time.time()
            if force or now - leg_state["last"] >= 0.5:
                global_pct = int(((leg_state["done"] + frac) / legs) * 100)
                pct = min(99, global_pct)
                emit(type="progress", stage="separate", pct=pct)
                if progress_callback:
                    progress_callback(pct, f"Separating stems: {pct}%")
                leg_state["last"] = now

    dapply.tqdm = types.SimpleNamespace(tqdm=ProgressTqdm) if is_module else ProgressTqdm

    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"

    if device == "cuda" and not torch.cuda.is_available():
        device = "cpu"

    emit(type="progress", stage="model", pct=0, message=f"Loading {model_name} on {device}")
    if progress_callback:
        progress_callback(0, f"Loading {model_name} on {device}...")

    from demucs.apply import apply_model
    from demucs.pretrained import get_model

    try:
        model = get_model(model_name)
    except Exception as e:
        fail(f"Model load failed: {e}")

    model.to(device)
    model.eval()
    leg_state["legs"] = max(1, len(getattr(model, "models", [1]))) * max(1, shifts)

    audio, sr = load_wav(input_path)
    target_sr = model.samplerate
    if sr != target_sr:
        import torchaudio

        t = torch.from_numpy(audio)
        t = torchaudio.functional.resample(t, sr, target_sr)
        audio = t.numpy()
        sr = target_sr
    if audio.shape[0] == 1:
        audio = np.repeat(audio, 2, axis=0)

    mix = torch.from_numpy(audio).to(device)[None]

    emit(type="progress", stage="separate", pct=0, message="Separating stems")
    try:
        sources = apply_model(
            model,
            mix,
            device=device,
            shifts=shifts,
            split=True,
            overlap=overlap,
            progress=True,
        )
    except Exception as e:
        if device != "cpu":
            emit(type="progress", stage="separate", pct=0, message=f"GPU failed ({e}), falling back to CPU")
            if progress_callback:
                progress_callback(0, "GPU memory exhausted, falling back to CPU...")
            model = model.cpu()
            mix = mix.cpu()
            device = "cpu"
            sources = apply_model(
                model,
                mix,
                device=device,
                shifts=shifts,
                split=True,
                overlap=overlap,
                progress=True,
            )
        else:
            fail(f"Separation failed: {e}")

    wanted = None
    if only:
        wanted = [s.strip() for s in only.split(",") if s.strip()]

    os.makedirs(out_dir, exist_ok=True)
    out_cpu = sources[0].cpu().numpy()
    written = []
    for i, name in enumerate(model.sources):
        if wanted is not None and name not in wanted:
            continue
        path = os.path.join(out_dir, f"{name}.wav")
        save_wav_f32(path, out_cpu[i], sr)
        written.append(name)
        emit(type="stem", name=name)

    # Clean GPU memory immediately after separation to free VRAM for BTC chord recognizer
    del sources
    del mix
    del model
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    emit(type="done", stems=written, out_dir=out_dir)
    return written


def main():
    parser = argparse.ArgumentParser(description="Song Chord Analyzer Demucs Stem Separator")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="htdemucs")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--shifts", type=int, default=1)
    parser.add_argument("--overlap", type=float, default=0.25)
    parser.add_argument("--only", default="bass,other")
    args = parser.parse_args()

    run_separation(
        input_path=args.input,
        out_dir=args.out,
        model_name=args.model,
        device=args.device,
        shifts=args.shifts,
        overlap=args.overlap,
        only=args.only,
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        fail(crash_message(e))
