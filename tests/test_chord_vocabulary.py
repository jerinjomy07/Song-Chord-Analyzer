"""
Unit tests for chord vocabulary, parsing, inversion calculation, and transposition.
"""

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))
from backend.chord.vocabulary import (
    parse_chord_string,
    calculate_inversion,
    normalize_pitch
)
from backend.transpose.transpose_engine import transpose_note, transpose_chord
from backend.models.schemas import ChordPrediction


def test_pitch_normalization():
    assert normalize_pitch("c#") == "C#"
    assert normalize_pitch("Db") == "C#"
    assert normalize_pitch("eb") == "D#"
    assert normalize_pitch("F#") == "F#"
    assert normalize_pitch("Bb") == "A#"


def test_chord_parsing_basic():
    root, qual, bass, inv, disp = parse_chord_string("C")
    assert root == "C" and qual == "maj" and bass == "C" and inv == 0 and disp == "C"

    root, qual, bass, inv, disp = parse_chord_string("Am")
    assert root == "A" and qual == "min" and bass == "A" and inv == 0 and disp == "Am"

    root, qual, bass, inv, disp = parse_chord_string("G7")
    assert root == "G" and qual == "7" and bass == "G" and inv == 0 and disp == "G7"

    root, qual, bass, inv, disp = parse_chord_string("F#maj7")
    assert root == "F#" and qual == "maj7" and bass == "F#" and inv == 0 and disp == "F#maj7"


def test_slash_chord_parsing_and_inversions():
    # F#/A# (1st inversion of F# Major: Third in bass)
    root, qual, bass, inv, disp = parse_chord_string("F#/A#")
    assert root == "F#"
    assert qual == "maj"
    assert bass == "A#"
    assert inv == 1
    assert disp == "F#/A#"

    # A/C# (1st inversion of A Major)
    root, qual, bass, inv, disp = parse_chord_string("A/C#")
    assert root == "A"
    assert qual == "maj"
    assert bass == "C#"
    assert inv == 1
    assert disp == "A/C#"

    # D/F# (1st inversion of D Major)
    root, qual, bass, inv, disp = parse_chord_string("D/F#")
    assert root == "D"
    assert qual == "maj"
    assert bass == "F#"
    assert inv == 1
    assert disp == "D/F#"

    # C/G (2nd inversion of C Major: Fifth in bass)
    root, qual, bass, inv, disp = parse_chord_string("C/G")
    assert root == "C"
    assert bass == "G"
    assert inv == 2


def test_chord_transposition():
    # A -> +2 semitones -> B
    c1 = ChordPrediction(
        root="A", quality="maj", bass="A", inversion=0, display="A",
        start_time=0.0, end_time=1.0, duration=1.0, confidence=0.95
    )
    tr1 = transpose_chord(c1, 2)
    assert tr1.root == "B"
    assert tr1.display == "B"

    # A/C# -> +2 semitones -> B/D#
    c2 = ChordPrediction(
        root="A", quality="maj", bass="C#", inversion=1, display="A/C#",
        start_time=0.0, end_time=1.0, duration=1.0, confidence=0.91
    )
    tr2 = transpose_chord(c2, 2)
    assert tr2.root == "B"
    assert tr2.bass == "D#"
    assert tr2.display == "B/D#"
    assert tr2.inversion == 1

    # F#m -> +2 semitones -> G#m
    c3 = ChordPrediction(
        root="F#", quality="min", bass="F#", inversion=0, display="F#m",
        start_time=0.0, end_time=1.0, duration=1.0, confidence=0.88
    )
    tr3 = transpose_chord(c3, 2)
    assert tr3.root == "G#"
    assert tr3.display == "G#m"


if __name__ == "__main__":
    test_pitch_normalization()
    test_chord_parsing_basic()
    test_slash_chord_parsing_and_inversions()
    test_chord_transposition()
    print("All unit tests passed successfully!")
