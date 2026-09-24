"""
Tests for Ground-Truth Evaluation Module.
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from backend.evaluation.evaluator import ChordAccuracyEvaluator, GroundTruthChord
from backend.models.schemas import SongAnalysis, AudioMetadata, PipelineMetadata, KeyAnalysis, TempoAnalysis, MeterAnalysis, BeatGrid, ChordPrediction


def test_evaluator():
    evaluator = ChordAccuracyEvaluator(time_step=0.5)

    # Simulated Ground Truth
    gt_chords = [
        GroundTruthChord(start_time=0.0, end_time=4.0, chord_label="A"),
        GroundTruthChord(start_time=4.0, end_time=8.0, chord_label="A/C#"),
        GroundTruthChord(start_time=8.0, end_time=12.0, chord_label="D"),
        GroundTruthChord(start_time=12.0, end_time=16.0, chord_label="E"),
    ]

    # Simulated Predictions (nearly perfect match with one slight quality variant)
    pred_chords = [
        ChordPrediction(root="A", quality="maj", bass="A", inversion=0, display="A", start_time=0.0, end_time=4.0, duration=4.0, confidence=0.95),
        ChordPrediction(root="A", quality="maj", bass="C#", inversion=1, display="A/C#", start_time=4.0, end_time=8.0, duration=4.0, confidence=0.92),
        ChordPrediction(root="D", quality="maj", bass="D", inversion=0, display="D", start_time=8.0, end_time=12.0, duration=4.0, confidence=0.94),
        ChordPrediction(root="E", quality="7", bass="E", inversion=0, display="E7", start_time=12.0, end_time=16.0, duration=4.0, confidence=0.90),
    ]

    dummy_analysis = SongAnalysis(
        id="eval_test",
        title="Test Song",
        metadata=AudioMetadata(filename="test.wav", duration=16.0, sample_rate=22050, channels=1, format="wav", file_size_bytes=1000, file_hash="hash123"),
        pipeline_metadata=PipelineMetadata(),
        key=KeyAnalysis(tonic="A", mode="major", display="A Major", confidence=0.95),
        tempo=TempoAnalysis(bpm=105.0, confidence=0.94),
        meter=MeterAnalysis(numerator=4, denominator=4, display="4/4"),
        beat_grid=BeatGrid(bpm=105.0, beats=[0.0, 1.0, 2.0, 3.0, 4.0]),
        sections=[],
        chords=pred_chords
    )

    report = evaluator.evaluate(
        predicted=dummy_analysis,
        ground_truth_chords=gt_chords,
        expected_key="A Major",
        expected_bpm=105.0,
        expected_meter="4/4"
    )

    print("Evaluator Report:")
    print(f"  Root Accuracy:      {report.root_accuracy_pct}%")
    print(f"  Quality Accuracy:   {report.quality_accuracy_pct}%")
    print(f"  Inversion Accuracy: {report.inversion_accuracy_pct}%")
    print(f"  Key Correct:        {report.key_correct}")
    print(f"  BPM Error:          {report.bpm_error_pct}%")
    assert report.root_accuracy_pct == 100.0
    assert report.inversion_accuracy_pct == 100.0
    assert report.key_correct is True
    assert report.bpm_error_pct == 0.0
    print("Evaluator tests passed successfully!")


if __name__ == "__main__":
    test_evaluator()
