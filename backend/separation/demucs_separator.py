"""
Stem separation module integrating Demucs.
Extracts 'bass' and 'other' accompaniment stems with GPU acceleration and CPU fallback.
Independent of external installations with automatic VRAM management.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Optional, Callable

from backend.config import STEMS_DIR, CUDA_AVAILABLE


class DemucsSeparator:
    def __init__(self, stems_root: Path = STEMS_DIR, model: str = "htdemucs"):
        self.stems_root = stems_root
        self.model = model

    def separate(
        self,
        audio_path: Path,
        file_hash: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Path]:
        """
        Separates audio into bass and other accompaniment stems.
        Caches separated stems by file hash.
        Returns dict with paths: {"bass": Path, "other": Path}
        """
        song_stems_dir = self.stems_root / file_hash
        song_stems_dir.mkdir(parents=True, exist_ok=True)

        bass_stem = song_stems_dir / "bass.wav"
        other_stem = song_stems_dir / "other.wav"

        # 1. Check local cache
        if bass_stem.exists() and other_stem.exists():
            if progress_callback:
                progress_callback(100, "Using cached separated stems")
            return {"bass": bass_stem, "other": other_stem}

        if progress_callback:
            progress_callback(5, "Initializing stem separation (bass + accompaniment)...")

        device = "cuda" if CUDA_AVAILABLE else "cpu"

        # 2. Run separation using integrated module
        try:
            from backend.separation.separate import run_separation

            run_separation(
                input_path=str(audio_path),
                out_dir=str(song_stems_dir),
                model_name=self.model,
                device=device,
                shifts=1,
                overlap=0.25,
                only="bass,other",
                progress_callback=progress_callback,
            )
        except Exception as e:
            print(f"[Demucs] In-process separation encountered {e}, running fallback...")
            self._fallback_direct_demucs(audio_path, song_stems_dir, device, progress_callback)

        return {"bass": bass_stem, "other": other_stem}

    def _fallback_direct_demucs(
        self,
        audio_path: Path,
        song_stems_dir: Path,
        device: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        """Direct Demucs separation fallback if needed."""
        import demucs.separate

        if progress_callback:
            progress_callback(20, "Running Demucs source separation...")

        cmd = [
            "-n", self.model,
            "-d", device,
            "--two-stems", "bass",
            "-o", str(song_stems_dir.parent),
            str(audio_path),
        ]
        demucs.separate.main(cmd)
