"""
Chroma and Harmonic Pitch Class Profile (HPCP) template-matching chord recognizer.
Provides signal-processing baseline for multi-source evidence fusion.
"""

from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
import librosa
import soundfile as sf

from backend.models.schemas import ChordPrediction
from backend.chord.base import ChordRecognizer
from backend.chord.vocabulary import ROOT_NAMES, parse_chord_string

CHORD_TEMPLATES = {
    'maj': [0, 4, 7],
    'min': [0, 3, 7],
    '7': [0, 4, 7, 10],
    'maj7': [0, 4, 7, 11],
    'min7': [0, 3, 7, 10],
    'sus4': [0, 5, 7],
    'sus2': [0, 2, 7],
    'dim': [0, 3, 6],
    'aug': [0, 4, 8],
}


class ChromaChordRecognizer(ChordRecognizer):
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate
        self.templates = self._build_template_matrix()

    def _build_template_matrix(self) -> Dict[str, np.ndarray]:
        """Precomputes normalized 12-dimensional chroma vectors for all roots and qualities."""
        templates = {}
        for root_idx, root in enumerate(ROOT_NAMES):
            for qual, intervals in CHORD_TEMPLATES.items():
                vec = np.zeros(12, dtype=np.float32)
                for interval in intervals:
                    pitch_idx = (root_idx + interval) % 12
                    vec[pitch_idx] = 1.0
                vec = vec / np.linalg.norm(vec)
                chord_name = root if qual == 'maj' else f"{root}:{qual}"
                templates[chord_name] = vec
        return templates

    def analyze(self, audio_path: Path, **kwargs) -> List[ChordPrediction]:
        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048, bins_per_octave=24)
        times = librosa.frames_to_time(np.arange(chroma.shape[1]), sr=sr, hop_length=2048)

        # Normalize chroma frames
        norms = np.linalg.norm(chroma, axis=0, keepdims=True)
        norms[norms == 0] = 1.0
        chroma_norm = chroma / norms

        predictions = []
        for i in range(chroma.shape[1]):
            frame_vec = chroma_norm[:, i]
            best_chord, best_sim = self.match_chroma_vector(frame_vec)
            predictions.append((times[i], best_chord, best_sim))

        return self._collapse_predictions(predictions, hop_duration=2048 / sr)

    def match_chroma_vector(self, chroma_vec: np.ndarray) -> Tuple[str, float]:
        """Returns top matching chord and cosine similarity for a single chroma vector."""
        if np.linalg.norm(chroma_vec) < 1e-4:
            return 'N', 1.0

        best_score = -1.0
        best_chord = 'N'

        for chord_name, template in self.templates.items():
            sim = float(np.dot(chroma_vec, template))
            if sim > best_score:
                best_score = sim
                best_chord = chord_name

        conf = float(np.clip(best_score, 0.4, 0.98))
        return best_chord, conf

    def predict_features(self, features: Any) -> List[ChordPrediction]:
        return []

    def _collapse_predictions(self, frame_preds: List[Tuple[float, str, float]], hop_duration: float) -> List[ChordPrediction]:
        if not frame_preds:
            return []

        segments = []
        curr_start, curr_chord, curr_conf = frame_preds[0]
        confs = [curr_conf]

        for t, chord, conf in frame_preds[1:]:
            if chord == curr_chord:
                confs.append(conf)
            else:
                end_time = t
                avg_conf = float(np.mean(confs))
                root, qual, bass, inv, display = parse_chord_string(curr_chord)
                segments.append(ChordPrediction(
                    root=root,
                    quality=qual,
                    bass=bass,
                    inversion=inv,
                    display=display,
                    start_time=round(curr_start, 3),
                    end_time=round(end_time, 3),
                    duration=round(end_time - curr_start, 3),
                    confidence=round(avg_conf, 2),
                    needs_review=(avg_conf < 0.65 and display != 'N')
                ))
                curr_start = t
                curr_chord = chord
                confs = [conf]

        end_time = frame_preds[-1][0] + hop_duration
        root, qual, bass, inv, display = parse_chord_string(curr_chord)
        segments.append(ChordPrediction(
            root=root,
            quality=qual,
            bass=bass,
            inversion=inv,
            display=display,
            start_time=round(curr_start, 3),
            end_time=round(end_time, 3),
            duration=round(end_time - curr_start, 3),
            confidence=round(float(np.mean(confs)), 2),
            needs_review=(float(np.mean(confs)) < 0.65 and display != 'N')
        ))

        return segments

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "name": "ChromaChordRecognizer",
            "type": "CQT-Chroma Template Matching",
            "vocabulary_size": 108,
            "license": "ISC"
        }
