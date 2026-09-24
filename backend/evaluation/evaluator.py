"""
Evaluation and accuracy benchmarking module.
Evaluates predicted chords, timing, key, BPM, and inversions against ground-truth chord annotations.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from pydantic import BaseModel

from backend.models.schemas import ChordPrediction, SongAnalysis
from backend.chord.vocabulary import parse_chord_string, PITCH_TO_SEMITONE


class EvaluationReport(BaseModel):
    song_title: str
    total_eval_duration_sec: float
    root_accuracy_pct: float
    quality_accuracy_pct: float
    inversion_accuracy_pct: float
    mirex_chord_overlap_pct: float
    key_correct: bool
    expected_key: str
    predicted_key: str
    bpm_error_pct: float
    expected_bpm: float
    predicted_bpm: float
    meter_correct: bool
    expected_meter: str
    predicted_meter: str
    discrepancies: List[Dict[str, Any]]


class GroundTruthChord(BaseModel):
    start_time: float
    end_time: float
    chord_label: str  # e.g. "A", "A/C#", "F#m", "D"


class ChordAccuracyEvaluator:
    def __init__(self, time_step: float = 0.1):
        self.time_step = time_step  # 100ms evaluation grid

    def evaluate(
        self,
        predicted: SongAnalysis,
        ground_truth_chords: List[GroundTruthChord],
        expected_key: str,
        expected_bpm: float,
        expected_meter: str
    ) -> EvaluationReport:
        """
        Calculates frame-by-frame MIR accuracy metrics:
        - Root accuracy
        - Quality accuracy
        - Inversion accuracy
        - MIREX chord overlap
        - Key, BPM, and Meter accuracy
        """
        duration = predicted.metadata.duration
        times = np.arange(0, duration, self.time_step)
        num_frames = len(times)

        root_matches = 0
        quality_matches = 0
        inversion_matches = 0
        full_matches = 0
        discrepancies = []

        for t in times:
            gt_chord_str = self._lookup_chord_at_time(ground_truth_chords, t)
            pred_chord_obj = self._lookup_pred_at_time(predicted.chords, t)
            
            gt_r, gt_q, gt_b, gt_inv, gt_disp = parse_chord_string(gt_chord_str)
            pr_r = pred_chord_obj.root
            pr_q = pred_chord_obj.quality
            pr_b = pred_chord_obj.bass
            pr_disp = pred_chord_obj.display

            # 1. Root comparison
            is_root_match = (gt_r == pr_r)
            if is_root_match:
                root_matches += 1

            # 2. Quality comparison
            is_qual_match = (gt_q == pr_q or (gt_q in ['maj', ''] and pr_q in ['maj', '']))
            if is_root_match and is_qual_match:
                quality_matches += 1

            # 3. Bass / Inversion comparison (measured when root matches or bass tone matches)
            is_inv_match = (gt_b == pr_b)
            if is_inv_match:
                inversion_matches += 1

            # 4. Full match
            if gt_disp == pr_disp:
                full_matches += 1
            else:
                # Log sample discrepancies every 2 seconds
                if len(discrepancies) < 25 and int(t * 10) % 20 == 0:
                    discrepancies.append({
                        "time": round(t, 2),
                        "expected": gt_disp,
                        "predicted": pr_disp,
                        "confidence": pred_chord_obj.confidence,
                        "failure_level": "Root" if not is_root_match else ("Quality" if not is_qual_match else "Inversion")
                    })

        root_acc = (root_matches / num_frames) * 100.0 if num_frames else 0.0
        qual_acc = (quality_matches / num_frames) * 100.0 if num_frames else 0.0
        inv_acc = (inversion_matches / num_frames) * 100.0 if num_frames else 0.0
        mirex_overlap = (full_matches / num_frames) * 100.0 if num_frames else 0.0

        bpm_diff = abs(predicted.tempo.bpm - expected_bpm) / expected_bpm * 100.0
        key_match = (predicted.key.display.lower() == expected_key.lower())
        meter_match = (predicted.meter.display == expected_meter)

        return EvaluationReport(
            song_title=predicted.title,
            total_eval_duration_sec=round(duration, 2),
            root_accuracy_pct=round(root_acc, 2),
            quality_accuracy_pct=round(qual_acc, 2),
            inversion_accuracy_pct=round(inv_acc, 2),
            mirex_chord_overlap_pct=round(mirex_overlap, 2),
            key_correct=key_match,
            expected_key=expected_key,
            predicted_key=predicted.key.display,
            bpm_error_pct=round(bpm_diff, 2),
            expected_bpm=expected_bpm,
            predicted_bpm=predicted.tempo.bpm,
            meter_correct=meter_match,
            expected_meter=expected_meter,
            predicted_meter=predicted.meter.display,
            discrepancies=discrepancies
        )

    def _lookup_chord_at_time(self, chords: List[GroundTruthChord], t: float) -> str:
        for c in chords:
            if c.start_time <= t < c.end_time:
                return c.chord_label
        return 'N'

    def _lookup_pred_at_time(self, chords: List[ChordPrediction], t: float) -> ChordPrediction:
        for c in chords:
            if c.start_time <= t < c.end_time:
                return c
        return chords[-1] if chords else ChordPrediction(
            root='N', quality='none', bass='N', inversion=0, display='N',
            start_time=0.0, end_time=0.0, duration=0.0, confidence=1.0
        )
