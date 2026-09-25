import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import glob
import json
from backend.beat.beat_tracker import BeatTracker
from backend.meter.meter_detector import MeterDetector

detector = MeterDetector()
tracker = BeatTracker()

print("=== TESTING GOLDEN METER DATASET ===")
for d in sorted(glob.glob("tests/golden_meter/*")):
    p = Path(d)
    audio_path = p / "audio.wav"
    gt_path = p / "ground_truth.json"
    if not audio_path.exists() or not gt_path.exists():
        continue
    with open(gt_path, "r", encoding="utf-8") as fp:
        gt = json.load(fp)
    beat_grid, tempo_info = tracker.track_beats(audio_path)
    meter_analysis, downbeats, pickup = detector.detect_meter(
        audio_path,
        beat_times=beat_grid.beats,
        bpm=tempo_info.selected_bpm or tempo_info.bpm,
        tempo_info=tempo_info
    )
    res = "MATCH" if meter_analysis.display == gt["meter"] else "MISMATCH"
    print(f"[{res}] {p.name}: Expected {gt['meter']} ({gt['expected_bpm']:.1f} bpm), Got {meter_analysis.display} (detected: {tempo_info.selected_bpm:.1f} bpm, conf={meter_analysis.confidence})")

print("\n=== TESTING REAL SONGS ===")
real_songs = [
    ("Bekhayali", Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/43f5b483/audio.mp3"), "3/4"),
    ("Pavzhamalli", Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/2dfd6d87/audio.mp3"), "2/4"),
    ("Magale", Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/30f48f40/audio.mp3"), "3/4"),
    ("Nallaru Po", Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/4bb5d8cb/audio.mp3"), "4/4"),
]

for name, path, expected_meter in real_songs:
    if not path.exists():
        print(f"Skipping {name}: file not found at {path}")
        continue
    beat_grid, tempo_info = tracker.track_beats(path)
    meter_analysis, downbeats, pickup = detector.detect_meter(
        path,
        beat_times=beat_grid.beats,
        bpm=tempo_info.selected_bpm or tempo_info.bpm,
        tempo_info=tempo_info
    )
    res = "MATCH" if meter_analysis.display == expected_meter else "MISMATCH"
    print(f"[{res}] {name}: Expected {expected_meter}, Got {meter_analysis.display} (BPM: {tempo_info.selected_bpm:.1f}, conf={meter_analysis.confidence})")
    print(f"       Evidence: {meter_analysis.meter_evidence}")
    print(f"       Candidate scores: {meter_analysis.candidate_scores}")
