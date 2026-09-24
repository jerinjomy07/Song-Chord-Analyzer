"""
Stem separation module integrating Demucs.
Reuses local StemKit components and cached htdemucs models.
Separates 'bass' and 'other' stems with GPU acceleration and CPU fallback.
"""

import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Optional, Callable

from backend.config import (
    STEMKIT_PYTHON,
    STEMS_DIR,
    CUDA_AVAILABLE,
    STEMKIT_PROGRAMS,
)


class DemucsSeparator:
    def __init__(self, stems_root: Path = STEMS_DIR, model: str = "htdemucs"):
        self.stems_root = stems_root
        self.model = model
        self.stemkit_script = STEMKIT_PROGRAMS / "resources" / "python" / "separate.py"

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

        # 2. Check if the audio file's directory already contains stems (e.g. from existing StemKit library)
        existing_stems_dir = audio_path.parent / "stems"
        if (existing_stems_dir / "bass.wav").exists() and (existing_stems_dir / "other.wav").exists():
            if progress_callback:
                progress_callback(95, "Found existing stems from StemKit library, importing...")
            shutil.copy2(existing_stems_dir / "bass.wav", bass_stem)
            shutil.copy2(existing_stems_dir / "other.wav", other_stem)
            if progress_callback:
                progress_callback(100, "Imported stems successfully")
            return {"bass": bass_stem, "other": other_stem}

        if progress_callback:
            progress_callback(5, "Initializing stem separation (bass + accompaniment)...")

        device = "cuda" if CUDA_AVAILABLE else "cpu"
        
        # Use StemKit's separate.py with --only bass,other
        if self.stemkit_script.exists() and STEMKIT_PYTHON.exists():
            cmd = [
                str(STEMKIT_PYTHON),
                str(self.stemkit_script),
                "--input", str(audio_path),
                "--out", str(song_stems_dir),
                "--model", self.model,
                "--device", device,
                "--only", "bass,other",
                "--shifts", "1",
                "--overlap", "0.25",
            ]
            
            try:
                # Merge stderr into stdout or use DEVNULL to prevent Windows pipe deadlocks
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )
                
                for line in proc.stdout:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get("type")
                        if msg_type == "progress":
                            pct = data.get("pct", 0)
                            msg = data.get("message", f"Separating stems: {pct}%")
                            if progress_callback:
                                progress_callback(pct, msg)
                        elif msg_type == "stem":
                            name = data.get("name")
                            if progress_callback:
                                progress_callback(90, f"Generated {name} stem")
                    except json.JSONDecodeError:
                        # Non-json logging messages from PyTorch or Demucs
                        pass
                        
                proc.wait()
                
                if proc.returncode != 0:
                    print(f"[Demucs] StemKit script returned code {proc.returncode}, attempting in-process fallback")
                    self._fallback_direct_demucs(audio_path, song_stems_dir, device, progress_callback)
            except Exception as e:
                print(f"[Demucs] Subprocess separation error: {e}, attempting in-process fallback")
                self._fallback_direct_demucs(audio_path, song_stems_dir, device, progress_callback)
        else:
            self._fallback_direct_demucs(audio_path, song_stems_dir, device, progress_callback)

        return {"bass": bass_stem, "other": other_stem}

    def _fallback_direct_demucs(
        self,
        audio_path: Path,
        song_stems_dir: Path,
        device: str,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ):
        """In-process Demucs separation fallback if script is unavailable."""
        import demucs.separate

        if progress_callback:
            progress_callback(20, "Running Demucs source separation...")

        cmd = [
            "-n", self.model,
            "-d", device,
            "--two-stems", "bass",
            "-o", str(song_stems_dir.parent),
            str(audio_path)
        ]
        demucs.separate.main(cmd)
