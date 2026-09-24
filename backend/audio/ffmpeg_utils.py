"""
Audio conversion and probing utilities using FFmpeg.
Safely extracts audio properties and converts files to standardized PCM WAV.
"""

import os
import subprocess
import hashlib
import json
from pathlib import Path
from typing import Tuple, Dict, Any
import soundfile as sf

from backend.config import FFMPEG_PATH


def compute_audio_hash(filepath: Path) -> str:
    """Computes SHA256 of the first 2MB and last 2MB + file size to quickly uniquely identify audio files."""
    hasher = hashlib.sha256()
    size = os.path.getsize(filepath)
    hasher.update(str(size).encode())
    
    with open(filepath, "rb") as f:
        # Read initial chunk
        hasher.update(f.read(2 * 1024 * 1024))
        if size > 4 * 1024 * 1024:
            f.seek(size - 2 * 1024 * 1024)
            hasher.update(f.read(2 * 1024 * 1024))
            
    return hasher.hexdigest()[:16]


def get_audio_metadata(filepath: Path) -> Dict[str, Any]:
    """Retrieves audio duration, sample rate, and channels."""
    try:
        info = sf.info(str(filepath))
        return {
            "duration": info.duration,
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "format": info.format,
            "file_size_bytes": os.path.getsize(filepath)
        }
    except Exception:
        # Fallback to ffprobe if soundfile cannot read format (e.g. some m4a/aac)
        ffprobe_path = FFMPEG_PATH.replace("ffmpeg.exe", "ffprobe.exe")
        if os.path.exists(ffprobe_path):
            cmd = [
                ffprobe_path, "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(filepath)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                fmt = data.get("format", {})
                stream = data.get("streams", [{}])[0]
                return {
                    "duration": float(fmt.get("duration", 0.0)),
                    "sample_rate": int(stream.get("sample_rate", 44100)),
                    "channels": int(stream.get("channels", 2)),
                    "format": fmt.get("format_name", "audio"),
                    "file_size_bytes": os.path.getsize(filepath)
                }
        raise ValueError(f"Could not read audio file metadata for {filepath}")


def convert_to_standard_wav(input_path: Path, output_path: Path, sample_rate: int = 44100, mono: bool = False) -> Path:
    """
    Converts any input audio file (MP3, WAV, FLAC, M4A) to a standardized PCM 16-bit or 32-bit float WAV.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    channels = "1" if mono else "2"
    cmd = [
        FFMPEG_PATH,
        "-y",
        "-i", str(input_path),
        "-vn",
        "-ar", str(sample_rate),
        "-ac", channels,
        "-c:a", "pcm_s16le",
        str(output_path)
    ]
    
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"FFmpeg conversion failed: {process.stderr[:400]}")
        
    return output_path
