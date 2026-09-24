"""
Beat and tempo tracking module.
Automatically detects BPM, beat positions, downbeats, and bar boundaries.
"""

from pathlib import Path
from typing import Tuple, List
import numpy as np
import librosa
import soundfile as sf

from backend.models.schemas import BeatGrid, TempoAnalysis


class BeatTracker:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def track_beats(self, audio_path: Path, meter_numerator: int = 4) -> Tuple[BeatGrid, TempoAnalysis]:
        """
        Detects BPM, beat timestamps, and downbeats (bar starts).
        """
        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        # Compute onset envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
        
        # Estimate tempo and beat frames
        tempo_arr, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env,
            sr=sr,
            hop_length=512,
            tightness=100
        )
        
        bpm = float(tempo_arr[0] if isinstance(tempo_arr, (np.ndarray, list)) else tempo_arr)
        
        # Normal range heuristic for music (60-180 BPM)
        if bpm < 55:
            bpm *= 2.0
        elif bpm > 190:
            bpm /= 2.0
        bpm = round(bpm, 1)

        # Convert beat frames to seconds
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=512).tolist()
        
        if len(beat_times) < 2:
            # Fallback for synthetic / un-metered audio
            duration = len(y) / sr
            sec_per_beat = 60.0 / bpm
            beat_times = list(np.arange(0, duration, sec_per_beat))

        # Downbeat detection: Determine phase of bar by finding highest average onset strength
        downbeats = self._detect_downbeats(onset_env, beat_frames, beat_times, meter_numerator, sr)

        confidence = 0.92 if len(beat_times) > 8 else 0.65
        tempo_info = TempoAnalysis(
            bpm=bpm,
            confidence=confidence,
            is_estimated=(confidence < 0.8)
        )
        
        beat_grid = BeatGrid(
            bpm=bpm,
            beats=beat_times,
            downbeats=downbeats
        )
        
        return beat_grid, tempo_info

    def _detect_downbeats(
        self,
        onset_env: np.ndarray,
        beat_frames: np.ndarray,
        beat_times: List[float],
        beats_per_bar: int,
        sr: int
    ) -> List[float]:
        """Identifies downbeats by testing all cyclic offsets for maximal onset energy."""
        if len(beat_frames) < beats_per_bar:
            return beat_times[::beats_per_bar] if beat_times else [0.0]

        energies = []
        for offset in range(beats_per_bar):
            indices = np.arange(offset, len(beat_frames), beats_per_bar)
            frames = np.clip(beat_frames[indices], 0, len(onset_env) - 1)
            mean_strength = np.mean(onset_env[frames])
            energies.append(mean_strength)

        best_offset = int(np.argmax(energies))
        downbeat_indices = np.arange(best_offset, len(beat_times), beats_per_bar)
        downbeats = [beat_times[i] for i in downbeat_indices]
        return downbeats
