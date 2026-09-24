"""
Audio preprocessing and normalization module.
Handles validation, resampling, volume normalization, and intermediate cache management.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
import numpy as np
import soundfile as sf
import librosa

from backend.config import CACHE_DIR, TARGET_SAMPLE_RATE, SEPARATION_SAMPLE_RATE
from backend.audio.ffmpeg_utils import get_audio_metadata, convert_to_standard_wav, compute_audio_hash


class AudioPreprocessor:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir

    def preprocess(self, input_path: Path) -> Tuple[Path, Path, Dict[str, Any]]:
        """
        Processes input audio:
        1. Validates metadata & integrity
        2. Computes unique hash
        3. Creates cached 44.1kHz stereo WAV (for Demucs)
        4. Creates cached 22.05kHz mono WAV (for MIR / Chord / Beat models)
        5. Normalizes audio dynamics
        Returns:
            (stereo_44k_path, mono_22k_path, metadata)
        """
        raw_meta = get_audio_metadata(input_path)
        if raw_meta["duration"] < 1.0:
            raise ValueError(f"Audio file is too short ({raw_meta['duration']:.1f}s). Minimum 1 second required.")
            
        file_hash = compute_audio_hash(input_path)
        
        stereo_44k_path = self.cache_dir / f"{file_hash}_44k_stereo.wav"
        mono_22k_path = self.cache_dir / f"{file_hash}_22k_mono.wav"
        
        # Check cache
        if not stereo_44k_path.exists():
            convert_to_standard_wav(input_path, stereo_44k_path, sample_rate=SEPARATION_SAMPLE_RATE, mono=False)
            
        if not mono_22k_path.exists():
            convert_to_standard_wav(input_path, mono_22k_path, sample_rate=TARGET_SAMPLE_RATE, mono=True)
            
            # Apply subtle loudness normalization on mono 22k file if needed
            y, sr = soundfile_load_normalized(mono_22k_path)
            sf.write(str(mono_22k_path), y, sr, subtype='PCM_16')

        meta = {
            "filename": input_path.name,
            "duration": raw_meta["duration"],
            "sample_rate": raw_meta["sample_rate"],
            "channels": raw_meta["channels"],
            "format": raw_meta["format"],
            "file_size_bytes": raw_meta["file_size_bytes"],
            "file_hash": file_hash
        }
        
        return stereo_44k_path, mono_22k_path, meta


def soundfile_load_normalized(path: Path) -> Tuple[np.ndarray, int]:
    """Loads audio and normalizes peak amplitude to prevent clipping and low-volume artifacts."""
    y, sr = sf.read(str(path))
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    peak = np.max(np.abs(y))
    if peak > 1e-4:
        y = y / peak * 0.95
    return y.astype(np.float32), sr
