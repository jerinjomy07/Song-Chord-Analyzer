"""
Time signature / meter estimation module.
Analyzes rhythmic periodicity across 2, 3, 4, 6, and 12 beat subdivisions.
"""

from pathlib import Path
from typing import List
import numpy as np
import librosa
import soundfile as sf

from backend.models.schemas import MeterAnalysis


class MeterDetector:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def detect_meter(self, audio_path: Path, beat_times: List[float], bpm: float) -> MeterAnalysis:
        """
        Estimates musical meter / time signature from beat onsets and rhythmic pulses.
        Supported: 4/4, 3/4, 2/4, 6/8, 12/8
        """
        if len(beat_times) < 8:
            return MeterAnalysis(numerator=4, denominator=4, display="4/4", confidence=0.70, is_estimated=True)

        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)
        beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=512)
        beat_frames = np.clip(beat_frames, 0, len(onset_env) - 1)
        
        # Beat strength signal
        beat_strengths = onset_env[beat_frames]
        
        # Calculate autocorrelation of beat strengths
        max_lag = min(16, len(beat_strengths) // 2)
        if max_lag < 4:
            return MeterAnalysis(numerator=4, denominator=4, display="4/4", confidence=0.75, is_estimated=True)
            
        autocorr = np.correlate(beat_strengths - np.mean(beat_strengths), beat_strengths - np.mean(beat_strengths), mode='full')
        half = len(autocorr) // 2
        lags = autocorr[half:half + max_lag]
        
        # Score potential bar lengths (2, 3, 4, 6)
        scores = {}
        for meter_beats, num, den, name in [
            (4, 4, 4, "4/4"),
            (3, 3, 4, "3/4"),
            (2, 2, 4, "2/4"),
            (6, 6, 8, "6/8"),
        ]:
            if meter_beats < len(lags):
                score = lags[meter_beats]
                # Prioritize 4/4 slightly as prevailing standard
                if meter_beats == 4:
                    score *= 1.15
                scores[(num, den, name)] = score

        best_meter = max(scores.items(), key=lambda x: x[1])
        (num, den, name), score = best_meter
        
        confidence = 0.90 if score > 0 else 0.70
        is_estimated = confidence < 0.85

        return MeterAnalysis(
            numerator=num,
            denominator=den,
            display=name,
            confidence=round(confidence, 2),
            is_estimated=is_estimated
        )
