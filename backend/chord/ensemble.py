"""
Multi-source Chord Fusion Engine (EnsembleChordAnalyzer).
Fuses original mix predictions, accompaniment stem predictions, sounding bass stem analysis,
and harmonic chroma evidence into standardized, inversion-aware ChordPrediction objects.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from backend.models.schemas import ChordPrediction, ChordCandidate
from backend.chord.vocabulary import (
    parse_chord_string,
    calculate_inversion,
    PITCH_TO_SEMITONE,
    ROOT_NAMES,
    QUALITY_DISPLAY_MAP,
    is_flat_key,
    format_chord_display,
    get_btc_index_map
)
from backend.chord.bass import BassStemAnalyzer


class EnsembleChordAnalyzer:
    def __init__(self, bass_analyzer: Optional[BassStemAnalyzer] = None):
        self.bass_analyzer = bass_analyzer or BassStemAnalyzer()
        self.idx_to_chord = get_btc_index_map()
        self.chord_to_idx = {v: k for k, v in self.idx_to_chord.items()}

    def fuse_beat_probabilities(
        self,
        mix_probs: np.ndarray,
        mix_times: np.ndarray,
        other_probs: Optional[np.ndarray],
        bass_data: Optional[Dict[str, Any]],
        beat_times: List[float],
        key_root: Optional[str] = None,
        key_mode: Optional[str] = None
    ) -> List[ChordPrediction]:
        """
        Performs true beat-synchronous probability pooling and multi-source evidence fusion:
        1. Pools neural posterior probabilities across the exact beat interval.
        2. Combines accompaniment stem (vocals removed) with original mix.
        3. Applies simplicity regularization (User Requirement 4 & 5).
        4. Detects sounding bass note from isolated bass stem for explicit slash/inversion chords.
        5. Formats key-aware enharmonics.
        """
        if not beat_times or len(beat_times) < 2:
            return []

        is_flat = is_flat_key(key_root, key_mode)
        time_unit = mix_times[1] - mix_times[0] if len(mix_times) > 1 else 0.0926
        fused_beat_chords: List[ChordPrediction] = []

        for i in range(len(beat_times) - 1):
            start_t = beat_times[i]
            end_t = beat_times[i + 1]

            # Frame indices covering this beat
            f_start = max(0, min(int(round(start_t / time_unit)), len(mix_probs) - 1))
            f_end = max(f_start + 1, min(int(round(end_t / time_unit)), len(mix_probs)))

            # 1. Pool probabilities from mix
            p_mix_beat = np.mean(mix_probs[f_start:f_end], axis=0)

            # 2. Pool probabilities from accompaniment stem if available
            n_idx = 169
            if other_probs is not None:
                o_start = max(0, min(f_start, len(other_probs) - 1))
                o_end = max(o_start + 1, min(f_end, len(other_probs)))
                p_other_beat = np.mean(other_probs[o_start:o_end], axis=0)

                # If accompaniment stem has music (not silence/N), give it priority (vocals removed)
                if p_other_beat[n_idx] < 0.50:
                    p_combined = 0.65 * p_other_beat + 0.35 * p_mix_beat
                else:
                    p_combined = p_mix_beat
            else:
                p_combined = p_mix_beat

            # If the original mix has active music (low N), do not allow accompaniment silence to leak N
            if p_mix_beat[n_idx] < 0.35:
                p_combined[n_idx] = min(p_combined[n_idx], p_mix_beat[n_idx])
                comb_sum = float(np.sum(p_combined))
                if comb_sum > 0:
                    p_combined = p_combined / comb_sum

            # 3. Decode pooled vector with Simplicity Regularization
            root, qual, conf, alts = self._decode_simplicity(p_combined)

            if root == 'N':
                fused_beat_chords.append(ChordPrediction(
                    root='N',
                    quality='none',
                    bass='N',
                    inversion=0,
                    display='N',
                    start_time=round(start_t, 3),
                    end_time=round(end_t, 3),
                    duration=round(end_t - start_t, 3),
                    confidence=round(conf, 2),
                    needs_review=False,
                    alternatives=[]
                ))
                continue

            # 4. Explicit Bass Stem Sounding Note Analysis
            final_bass = root
            final_inversion = 0

            if bass_data is not None:
                bass_note, bass_conf = self.bass_analyzer.get_bass_note_at_interval(bass_data, start_t, end_t)
                if bass_note and bass_conf >= 0.52 and bass_note != root:
                    is_legit_slash, inv_num = self._is_valid_slash_or_inversion(root, qual, bass_note)
                    if is_legit_slash:
                        final_bass = bass_note
                        final_inversion = inv_num
                        conf = min(0.99, max(conf, bass_conf))

            # 5. Format display with key-aware enharmonics
            display = format_chord_display(root, qual, final_bass, is_flat=is_flat)

            fused_beat_chords.append(ChordPrediction(
                root=root,
                quality=qual,
                bass=final_bass,
                inversion=final_inversion,
                display=display,
                start_time=round(start_t, 3),
                end_time=round(end_t, 3),
                duration=round(end_t - start_t, 3),
                confidence=round(conf, 2),
                needs_review=(conf < 0.55),
                alternatives=alts
            ))

        return fused_beat_chords

    def _decode_simplicity(
        self,
        p_vector: np.ndarray
    ) -> Tuple[str, str, float, List[ChordCandidate]]:
        """
        Decodes a pooled probability vector with simplicity regularization:
        Prefers the base triad unless the extended chord (7, maj7, min7) has decisive evidence.
        """
        top_idx = int(np.argmax(p_vector))
        top_chord = self.idx_to_chord.get(top_idx, 'N')
        top_prob = float(p_vector[top_idx])

        if top_chord == 'N' or top_chord == 'X':
            return 'N', 'none', top_prob, []

        root, qual, _, _, _ = parse_chord_string(top_chord)

        # Build candidate alternatives list
        sorted_indices = np.argsort(p_vector)[::-1][:4]
        alts = []
        for a_idx in sorted_indices:
            if a_idx != top_idx and p_vector[a_idx] > 0.08:
                a_str = self.idx_to_chord.get(int(a_idx), 'N')
                _, _, _, _, a_disp = parse_chord_string(a_str)
                alts.append(ChordCandidate(chord=a_disp, probability=round(float(p_vector[a_idx]), 2)))

        # REQUIREMENT 4 & 5: Simplicity Regularization
        final_qual = qual
        final_prob = top_prob

        if qual in ['7', 'maj7', 'min7', 'maj6', 'min6', 'dim7', 'hdim7']:
            base_qual = 'min' if qual in ['min7', 'min6', 'hdim7'] else ('dim' if qual == 'dim7' else 'maj')
            base_str = root if base_qual == 'maj' else f"{root}:{base_qual}"
            base_idx = self.chord_to_idx.get(base_str)

            if base_idx is not None:
                base_prob = float(p_vector[base_idx])
                # Simplicity Regularization:
                # In popular/film/folk music, heavily favor base triads.
                # Avoid over-predicting complex jazz/extended chords (maj7, m6, dim) unless evidence is overwhelming (>= 0.85).
                # Keep standard sevenths (7, min7) only when clearly present (>= 0.65).
                if qual in ['maj7', 'maj6', 'min6', 'dim7', 'hdim7']:
                    keep_extension = (top_prob >= 0.85) and (top_prob > base_prob * 1.8) and (top_prob - base_prob >= 0.25)
                else:
                    keep_extension = (top_prob >= 0.65) and (top_prob > base_prob * 1.4) and (top_prob - base_prob >= 0.15)

                if not keep_extension:
                    # Simplify to base triad
                    final_qual = base_qual
                    final_prob = min(0.99, round(top_prob + base_prob, 2))
                    _, _, _, _, ext_disp = parse_chord_string(top_chord)
                    alts.insert(0, ChordCandidate(chord=ext_disp, probability=round(top_prob, 2)))

        return root, final_qual, final_prob, alts[:3]

    def _is_valid_slash_or_inversion(self, root: str, quality: str, bass: str) -> Tuple[bool, int]:
        """Checks if bass note represents a valid inversion (1st, 2nd, 3rd) or musical slash chord."""
        if not bass or bass == root or root == 'N' or bass == 'N':
            return False, 0

        root_semi = PITCH_TO_SEMITONE.get(root, 0)
        bass_semi = PITCH_TO_SEMITONE.get(bass, 0)
        interval = (bass_semi - root_semi) % 12

        # 1st Inversion: Third in bass (4 semitones for Major, 3 for Minor)
        if (quality in ['maj', '7', 'maj7', 'sus4', ''] and interval == 4) or \
           (quality in ['min', 'min7', 'dim', 'hdim7'] and interval == 3):
            return True, 1

        # 2nd Inversion: Fifth in bass (7 semitones)
        if interval == 7:
            return True, 2

        # 3rd Inversion: Seventh in bass (10 semitones for dom7/min7, 11 for maj7)
        if interval in [10, 11]:
            return True, 3

        # Common valid pop/worship slash chords (e.g. D/B -> Bm7, G/E -> Em7, C/A -> Am7, C/D -> D9sus, F/G -> G9sus)
        if interval in [2, 5, 9]:
            return True, 1

        return False, 0

    def fuse(
        self,
        mix_chords: List[ChordPrediction],
        other_chords: Optional[List[ChordPrediction]],
        bass_data: Optional[Dict[str, Any]],
        beat_times: List[float],
        key_root: Optional[str] = None,
        key_mode: Optional[str] = None
    ) -> List[ChordPrediction]:
        """Backwards-compatible segment-based fallback."""
        if not beat_times or len(beat_times) < 2:
            return mix_chords

        is_flat = is_flat_key(key_root, key_mode)
        fused: List[ChordPrediction] = []

        for i in range(len(beat_times) - 1):
            start_t = beat_times[i]
            end_t = beat_times[i + 1]
            mid_t = (start_t + end_t) / 2.0

            mix_pred = self._find_chord_at_time(mix_chords, mid_t)
            other_pred = self._find_chord_at_time(other_chords, mid_t) if other_chords else None

            # Pick best available
            chosen = other_pred if (other_pred and other_pred.root != 'N' and other_pred.confidence > 0.65) else mix_pred
            if not chosen:
                continue

            root = chosen.root
            qual = chosen.quality
            conf = chosen.confidence
            final_bass = root
            inv = 0

            if bass_data is not None and root != 'N':
                bass_note, bass_conf = self.bass_analyzer.get_bass_note_at_interval(bass_data, start_t, end_t)
                if bass_note and bass_conf >= 0.55 and bass_note != root:
                    is_slash, inv_num = self._is_valid_slash_or_inversion(root, qual, bass_note)
                    if is_slash:
                        final_bass = bass_note
                        inv = inv_num

            display = format_chord_display(root, qual, final_bass, is_flat=is_flat)

            fused.append(ChordPrediction(
                root=root,
                quality=qual,
                bass=final_bass,
                inversion=inv,
                display=display,
                start_time=round(start_t, 3),
                end_time=round(end_t, 3),
                duration=round(end_t - start_t, 3),
                confidence=round(conf, 2),
                needs_review=(conf < 0.55),
                alternatives=chosen.alternatives
            ))

        return fused

    def _find_chord_at_time(self, chords: Optional[List[ChordPrediction]], t: float) -> Optional[ChordPrediction]:
        if not chords:
            return None
        for c in chords:
            if c.start_time <= t <= c.end_time:
                return c
        return chords[-1] if chords else None
