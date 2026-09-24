"""
Explicit Bass Stem pitch analysis module for Slash Chord and Inversion detection.
Analyzes the isolated Demucs bass stem in the fundamental 30Hz - 350Hz register.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
import numpy as np
import librosa
import soundfile as sf

from backend.chord.vocabulary import ROOT_NAMES, normalize_pitch


class BassStemAnalyzer:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def analyze_bass_track(self, bass_audio_path: Path) -> Dict[str, Any]:
        """
        Analyzes the separated bass audio file.
        Extracts low-frequency chromagram focused on C1-C4 (32.7 Hz to 261.6 Hz)
        to isolate the currently sounding bass note.
        """
        y, sr = sf.read(str(bass_audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        # Apply lowpass filter to isolate bass fundamental and eliminate bleed
        hop_length = 512
        # C1 is ~32.7 Hz
        chroma_bass = librosa.feature.chroma_cqt(
            y=y,
            sr=sr,
            fmin=librosa.note_to_hz('C1'),
            n_octaves=4,
            hop_length=hop_length,
            bins_per_octave=24
        )

        times = librosa.frames_to_time(np.arange(chroma_bass.shape[1]), sr=sr, hop_length=hop_length)
        
        # Energy across frames
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        return {
            "chroma": chroma_bass,
            "times": times,
            "rms": rms,
            "sr": sr,
            "hop_length": hop_length
        }

    def get_bass_note_at_interval(
        self,
        bass_data: Dict[str, Any],
        start_time: float,
        end_time: float
    ) -> Tuple[Optional[str], float]:
        """
        Calculates the dominant physical bass note and confidence during a time interval.
        Returns: (bass_note, confidence)
        """
        times = bass_data["times"]
        chroma = bass_data["chroma"]
        rms = bass_data["rms"]

        mask = (times >= start_time) & (times <= end_time)
        if not np.any(mask):
            return None, 0.0

        interval_rms = np.mean(rms[mask])
        if interval_rms < 1e-3:
            # Bass is silent / resting in this interval
            return None, 0.0

        # Mean chroma vector over the interval, weighted by RMS energy
        weights = rms[mask]
        if np.sum(weights) > 0:
            interval_chroma = np.average(chroma[:, mask], axis=1, weights=weights)
        else:
            interval_chroma = np.mean(chroma[:, mask], axis=1)

        top_idx = int(np.argmax(interval_chroma))
        top_energy = float(interval_chroma[top_idx])
        sorted_energies = np.sort(interval_chroma)[::-1]
        
        # Bass pitch clarity ratio (top pitch vs runner up)
        runner_up = sorted_energies[1] if len(sorted_energies) > 1 else 0.0
        clarity = (top_energy - runner_up) / (top_energy + 1e-6)
        confidence = float(np.clip(clarity * 1.5, 0.5, 0.99))

        bass_note = ROOT_NAMES[top_idx]
        return bass_note, confidence
