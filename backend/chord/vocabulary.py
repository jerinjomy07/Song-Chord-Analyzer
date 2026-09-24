"""
Musical vocabulary definitions, chord templates, enharmonics, and string parsing.
Provides two-way mapping between raw model labels and structured ChordPrediction objects.
"""

from typing import Tuple, Dict, Optional, List
import re

ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
PITCH_TO_SEMITONE = {name: i for i, name in enumerate(ROOT_NAMES)}

# Quality list matching BTC 170-chord vocabulary
BTC_QUALITIES = [
    'min', 'maj', 'dim', 'aug', 'min6', 'maj6',
    'min7', 'minmaj7', 'maj7', '7', 'dim7', 'hdim7',
    'sus2', 'sus4'
]

# Standard musician display quality abbreviations
QUALITY_DISPLAY_MAP = {
    'maj': '',
    'min': 'm',
    'dim': 'dim',
    'aug': 'aug',
    'min6': 'm6',
    'maj6': '6',
    'min7': 'm7',
    'minmaj7': 'm(maj7)',
    'maj7': 'maj7',
    '7': '7',
    'dim7': 'dim7',
    'hdim7': 'm7b5',
    'sus2': 'sus2',
    'sus4': 'sus4',
    'add9': 'add9'
}

# Enharmonic normalization to standard sharp notation
ENHARMONIC_FLAT_TO_SHARP = {
    'Db': 'C#',
    'Eb': 'D#',
    'Gb': 'F#',
    'Ab': 'G#',
    'Bb': 'A#',
    'Cb': 'B',
    'Fb': 'E',
    'B#': 'C',
    'E#': 'F'
}

ENHARMONIC_SHARP_TO_FLAT = {
    'C#': 'Db',
    'D#': 'Eb',
    'F#': 'Gb',
    'G#': 'Ab',
    'A#': 'Bb'
}

FLAT_KEYS = {'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Dm', 'Gm', 'Cm', 'Fm', 'Bbm', 'Ebm'}
SHARP_KEYS = {'G', 'D', 'A', 'E', 'B', 'F#', 'Em', 'Bm', 'F#m', 'C#m', 'G#m'}

def is_flat_key(key_root: Optional[str], key_mode: Optional[str] = None) -> bool:
    """Returns True if the key signature uses flats instead of sharps."""
    if not key_root:
        return False
    norm_root = normalize_pitch(key_root)
    mode = (key_mode or "major").lower()

    if "min" in mode:
        # Minor keys with flats: Dm (1b), Gm (2b), Cm (3b), Fm (4b), Bbm (5b), Ebm (6b)
        return norm_root in ['D', 'G', 'C', 'F', 'A#', 'D#']
    else:
        # Major keys with flats: F (1b), Bb (2b), Eb (3b), Ab (4b), Db (5b), Gb (6b)
        return norm_root in ['F', 'A#', 'D#', 'G#', 'C#']

def get_enharmonic_pitch(pitch: str, is_flat: bool = False) -> str:
    """Converts pitch to flat or sharp notation depending on key signature."""
    pitch = normalize_pitch(pitch)
    if is_flat:
        return ENHARMONIC_SHARP_TO_FLAT.get(pitch, pitch)
    return pitch

def format_chord_display(root: str, quality: str, bass: str, is_flat: bool = False) -> str:
    """Formats musician-ready chord display with key-aware enharmonics and slash notation."""
    if root == 'N' or root == 'X':
        return 'N'

    disp_root = get_enharmonic_pitch(root, is_flat=is_flat)
    qual_disp = QUALITY_DISPLAY_MAP.get(quality, quality)
    display = f"{disp_root}{qual_disp}"

    if bass and bass != root and bass != 'N':
        disp_bass = get_enharmonic_pitch(bass, is_flat=is_flat)
        display = f"{display}/{disp_bass}"

    return display

def normalize_pitch(pitch: str) -> str:
    """Normalizes pitch spelling to standard representation."""
    pitch = pitch.strip()
    if not pitch:
        return 'C'
    pitch = pitch[0].upper() + pitch[1:].lower()
    return ENHARMONIC_FLAT_TO_SHARP.get(pitch, pitch)


def get_btc_index_map() -> Dict[int, str]:
    """Generates the 170-chord mapping from index to chord label."""
    idx_map = {169: 'N', 168: 'X'}
    for i in range(168):
        root_idx = i // 14
        quality_idx = i % 14
        root = ROOT_NAMES[root_idx]
        quality = BTC_QUALITIES[quality_idx]
        if quality_idx == 1:  # 'maj'
            chord_str = root
        else:
            chord_str = f"{root}:{quality}"
        idx_map[i] = chord_str
    return idx_map


def parse_chord_string(chord_str: str) -> Tuple[str, str, str, int, str]:
    """
    Parses a raw chord label (e.g. 'F#:maj', 'A/C#', 'C:min7', 'N') into:
    (root, quality, bass, inversion, display_string)
    """
    chord_str = chord_str.strip()
    if chord_str in ['N', 'X', 'None', '', 'no_chord']:
        return ('N', 'none', 'N', 0, 'N')

    # Check for slash chord: e.g. "F#/A#" or "A/C#" or "D:maj/F#"
    bass = None
    if '/' in chord_str:
        parts = chord_str.split('/', 1)
        chord_str = parts[0].strip()
        bass = normalize_pitch(parts[1].strip())

    # Check for colon notation: "F#:min7"
    if ':' in chord_str:
        parts = chord_str.split(':', 1)
        root = normalize_pitch(parts[0])
        quality = parts[1].strip()
    else:
        # Match root note from start of string
        match = re.match(r"^([A-Ga-g][#b]?)(.*)$", chord_str)
        if match:
            root = normalize_pitch(match.group(1))
            raw_qual = match.group(2).strip()
            if not raw_qual:
                quality = 'maj'
            elif raw_qual in ['m', 'min']:
                quality = 'min'
            elif raw_qual in ['7', 'dom7']:
                quality = '7'
            elif raw_qual in ['maj7', 'M7']:
                quality = 'maj7'
            elif raw_qual in ['m7', 'min7']:
                quality = 'min7'
            elif raw_qual in ['sus4', 'sus']:
                quality = 'sus4'
            elif raw_qual in ['sus2']:
                quality = 'sus2'
            elif raw_qual in ['dim']:
                quality = 'dim'
            elif raw_qual in ['aug']:
                quality = 'aug'
            else:
                quality = raw_qual
        else:
            root = 'C'
            quality = 'maj'

    if not bass:
        bass = root

    inversion = 0
    if bass != root:
        inversion = calculate_inversion(root, quality, bass)

    # Format musician display string
    qual_display = QUALITY_DISPLAY_MAP.get(quality, quality)
    display = f"{root}{qual_display}"
    if bass != root:
        display = f"{display}/{bass}"

    return (root, quality, bass, inversion, display)


def calculate_inversion(root: str, quality: str, bass: str) -> int:
    """Calculates musical inversion number (0=root, 1=1st, 2=2nd, 3=3rd)."""
    root_semi = PITCH_TO_SEMITONE.get(root, 0)
    bass_semi = PITCH_TO_SEMITONE.get(bass, 0)
    interval = (bass_semi - root_semi) % 12

    # 1st inversion (3rd in bass): 4 semitones (maj3) or 3 semitones (min3)
    if interval in [3, 4]:
        return 1
    # 2nd inversion (5th in bass): 7 semitones (perfect 5th) or 6 (dim 5th) or 8 (aug 5th)
    elif interval in [6, 7, 8]:
        return 2
    # 3rd inversion (7th in bass): 10 semitones (min7) or 11 semitones (maj7)
    elif interval in [10, 11]:
        return 3
    return 1  # General slash chord
