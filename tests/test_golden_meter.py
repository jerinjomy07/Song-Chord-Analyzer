"""
Automated unit & regression test suite for musical meter, tempo, downbeat,
and bar boundary identification across all six supported meters:
2/4, 3/4, 4/4, 6/8, 7/8, 12/8.
Runs with standard Python unittest or pytest.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.meter.meter_detector import MeterDetector, MeterDetectionResult


GOLDEN_DIR = Path(__file__).resolve().parent / "golden_meter"
LIBRARY_DIR = Path("C:/Users/jerin/AppData/Local/SongChordAnalyzer/library")

GOLDEN_TEST_CASES = [
    ("12_8", GOLDEN_DIR / "12_8" / "audio.wav", 12, 8, "12/8"),
    ("2_4", GOLDEN_DIR / "2_4" / "audio.wav", 2, 4, "2/4"),
    ("3_4", GOLDEN_DIR / "3_4" / "audio.wav", 3, 4, "3/4"),
    ("4_4", GOLDEN_DIR / "4_4" / "audio.wav", 4, 4, "4/4"),
    ("6_8", GOLDEN_DIR / "6_8" / "audio.wav", 6, 8, "6/8"),
    ("7_8", GOLDEN_DIR / "7_8" / "audio.wav", 7, 8, "7/8"),
]

REAL_LIBRARY_CASES = [
    ("Bekhayali", LIBRARY_DIR / "43f5b483" / "audio.mp3", 3, 4, "3/4"),
    ("Pavzhamalli", LIBRARY_DIR / "2dfd6d87" / "audio.mp3", 2, 4, "2/4"),
    ("Magale", LIBRARY_DIR / "30f48f40" / "audio.mp3", 3, 4, "3/4"),
    ("Nallaru Po", LIBRARY_DIR / "4bb5d8cb" / "audio.mp3", 4, 4, "4/4"),
]


class TestGoldenMeter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = MeterDetector()

    def test_golden_12_8(self):
        self._assert_meter("12_8", GOLDEN_DIR / "12_8" / "audio.wav", 12, 8, "12/8")

    def test_golden_2_4(self):
        self._assert_meter("2_4", GOLDEN_DIR / "2_4" / "audio.wav", 2, 4, "2/4")

    def test_golden_3_4(self):
        self._assert_meter("3_4", GOLDEN_DIR / "3_4" / "audio.wav", 3, 4, "3/4")

    def test_golden_4_4(self):
        self._assert_meter("4_4", GOLDEN_DIR / "4_4" / "audio.wav", 4, 4, "4/4")

    def test_golden_6_8(self):
        self._assert_meter("6_8", GOLDEN_DIR / "6_8" / "audio.wav", 6, 8, "6/8")

    def test_golden_7_8(self):
        self._assert_meter("7_8", GOLDEN_DIR / "7_8" / "audio.wav", 7, 8, "7/8")

    def test_real_bekhayali_3_4(self):
        p = LIBRARY_DIR / "43f5b483" / "audio.mp3"
        if not p.exists():
            self.skipTest("Bekhayali audio not found in library")
        self._assert_meter("Bekhayali", p, 3, 4, "3/4")

    def test_real_pavzhamalli_2_4(self):
        p = LIBRARY_DIR / "2dfd6d87" / "audio.mp3"
        if not p.exists():
            self.skipTest("Pavzhamalli audio not found in library")
        self._assert_meter("Pavzhamalli", p, 2, 4, "2/4")

    def test_real_magale_3_4(self):
        p = LIBRARY_DIR / "30f48f40" / "audio.mp3"
        if not p.exists():
            self.skipTest("Magale audio not found in library")
        self._assert_meter("Magale", p, 3, 4, "3/4")

    def test_real_nallaru_po_4_4(self):
        p = LIBRARY_DIR / "4bb5d8cb" / "audio.mp3"
        if not p.exists():
            self.skipTest("Nallaru Po audio not found in library")
        self._assert_meter("Nallaru Po", p, 4, 4, "4/4")

    def _assert_meter(self, name: str, path: Path, exp_num: int, exp_den: int, exp_display: str):
        self.assertTrue(path.exists(), f"File {path} not found")
        res = self.detector.detect_meter(audio_path=path)
        self.assertIsInstance(res, (tuple, MeterDetectionResult))
        meter_info, downbeats, pickup = res

        print(f"\n[{name}] Detected: {meter_info.display} ({res.selected_bpm:.1f} BPM, conf={meter_info.confidence}) | Expected: {exp_display}")
        self.assertEqual(meter_info.numerator, exp_num, f"[{name}] Numerator mismatch")
        self.assertEqual(meter_info.denominator, exp_den, f"[{name}] Denominator mismatch")
        self.assertEqual(meter_info.display, exp_display, f"[{name}] Display string mismatch")
        self.assertGreater(len(downbeats), 0, f"[{name}] Empty downbeats")
        self.assertGreater(meter_info.confidence, 0.0, f"[{name}] Zero confidence")


if __name__ == "__main__":
    unittest.main(verbosity=2)
