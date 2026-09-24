"""
Multi-source Musical Key and Mode detection module.
Fuses:
1. Harmonic Profile correlation (Krumhansl-Schmuckler / Temperley on CQT Chroma)
2. Global Chroma Pitch Class energy concentration
3. Chord sequence tonic stability and harmonic progression analysis
"""

from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import librosa
import soundfile as sf

from backend.models.schemas import KeyAnalysis, ChordPrediction
from backend.chord.vocabulary import ROOT_NAMES, PITCH_TO_SEMITONE

# Krumhansl-Kessler / Temperley Key Profiles
MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


class KeyDetector:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def detect_key(
        self,
        audio_path: Path,
        detected_chords: Optional[List[ChordPrediction]] = None
    ) -> KeyAnalysis:
        """
        Multi-source key detection fusing:
        - Estimator A: Profile correlation on CQT chroma
        - Estimator B: Chroma energy distribution
        - Estimator C: Chord progression tonic stability (if chords available)
        """
        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        # Compute harmonic chromagram (using CQT chroma)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=2048, bins_per_octave=24)
        chroma_vector = np.mean(chroma, axis=1)
        if np.linalg.norm(chroma_vector) > 0:
            chroma_vector = chroma_vector / np.linalg.norm(chroma_vector)

        # Estimator A: Profile correlation
        profile_scores = self._score_profiles(chroma_vector)

        # Estimator B: Triad energy concentration
        triad_scores = self._score_triad_energy(chroma_vector)

        # Estimator C: Chord sequence evidence (if provided)
        chord_scores = self._score_chord_sequence(detected_chords) if detected_chords else {}

        # Multi-source fusion
        combined_candidates = []
        for tonic in ROOT_NAMES:
            for mode in ["major", "minor"]:
                key_tuple = (tonic, mode)
                score_a = profile_scores.get(key_tuple, 0.0)
                score_b = triad_scores.get(key_tuple, 0.0)
                score_c = chord_scores.get(key_tuple, 0.0)

                # Weighted fusion: Profile (45%), Triad Energy (30%), Chord Sequence (25%)
                if chord_scores:
                    total_score = 0.45 * score_a + 0.30 * score_b + 0.25 * score_c
                else:
                    total_score = 0.60 * score_a + 0.40 * score_b

                combined_candidates.append((tonic, mode, total_score))

        combined_candidates.sort(key=lambda x: x[2], reverse=True)
        best_tonic, best_mode, best_score = combined_candidates[0]
        runner_up_score = combined_candidates[1][2]

        # Calculate confidence from the score difference between top 2 candidates
        margin = max(0.0, best_score - runner_up_score)
        conf = float(np.clip(0.65 + margin * 1.5, 0.60, 0.99))

        from backend.chord.vocabulary import is_flat_key, get_enharmonic_pitch
        disp_tonic = get_enharmonic_pitch(best_tonic, is_flat=is_flat_key(best_tonic, best_mode))
        display = f"{disp_tonic} {best_mode.capitalize()}"

        return KeyAnalysis(
            tonic=disp_tonic,
            mode=best_mode,
            display=display,
            confidence=round(conf, 2)
        )

    def _score_profiles(self, chroma_vector: np.ndarray) -> Dict[Tuple[str, str], float]:
        """Correlates rotated chroma with Major and Minor profiles."""
        scores = {}
        for i in range(12):
            tonic = ROOT_NAMES[i]
            shifted = np.roll(chroma_vector, -i)
            corr_maj = float(np.corrcoef(shifted, MAJOR_PROFILE)[0, 1])
            corr_min = float(np.corrcoef(shifted, MINOR_PROFILE)[0, 1])
            # Normalize correlation to 0-1
            scores[(tonic, "major")] = max(0.0, (corr_maj + 1.0) / 2.0)
            scores[(tonic, "minor")] = max(0.0, (corr_min + 1.0) / 2.0)
        return scores

    def _score_triad_energy(self, chroma_vector: np.ndarray) -> Dict[Tuple[str, str], float]:
        """Scores each key by the concentrated energy on its root, third, and fifth."""
        scores = {}
        for i in range(12):
            tonic = ROOT_NAMES[i]
            # Major triad: root (0), major 3rd (4), perfect 5th (7)
            maj_energy = chroma_vector[i] + chroma_vector[(i + 4) % 12] + chroma_vector[(i + 7) % 12]
            # Minor triad: root (0), minor 3rd (3), perfect 5th (7)
            min_energy = chroma_vector[i] + chroma_vector[(i + 3) % 12] + chroma_vector[(i + 7) % 12]

            scores[(tonic, "major")] = float(maj_energy / 3.0)
            scores[(tonic, "minor")] = float(min_energy / 3.0)
        return scores

    def _score_chord_sequence(self, chords: List[ChordPrediction]) -> Dict[Tuple[str, str], float]:
        """Analyzes root distribution and cadence endings from detected chords."""
        scores = {}
        if not chords:
            return scores

        # Tally root occurrences
        root_counts = {r: 0.0 for r in ROOT_NAMES}
        total_valid = 0.0

        for c in chords:
            if c.root in root_counts:
                root_counts[c.root] += c.duration
                total_valid += c.duration

        if total_valid == 0:
            return scores

        # Final chord bonus (often resolves to tonic)
        final_chord = next((c for c in reversed(chords) if c.root in root_counts), None)

        for tonic, count in root_counts.items():
            base_score = count / total_valid
            if final_chord and final_chord.root == tonic:
                base_score += 0.20

            scores[(tonic, "major")] = base_score
            scores[(tonic, "minor")] = base_score

        return scores
