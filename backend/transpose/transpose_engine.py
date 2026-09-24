"""
Transposition engine for songs, sections, bars, and chords.
Preserves chord quality, physical root, slash chord bass, and musical enharmonic spelling.
"""

from typing import List
from backend.models.schemas import (
    SongAnalysis,
    ChordPrediction,
    MusicalSection,
    Bar,
    KeyAnalysis
)
from backend.chord.vocabulary import (
    PITCH_TO_SEMITONE,
    ROOT_NAMES,
    ENHARMONIC_FLAT_TO_SHARP,
    ENHARMONIC_SHARP_TO_FLAT,
    QUALITY_DISPLAY_MAP,
    calculate_inversion
)

# Standard circle-of-fifths enharmonic preference maps
FLAT_KEYS = ['F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Dm', 'Gm', 'Cm', 'Fm', 'Bbm']


def transpose_note(note: str, semitones: int, prefer_flats: bool = False) -> str:
    """Transposes a single pitch class by N semitones, respecting key signature spelling."""
    if note in ['N', 'X', '']:
        return note

    # Normalize note
    normalized = ENHARMONIC_FLAT_TO_SHARP.get(note, note)
    curr_semi = PITCH_TO_SEMITONE.get(normalized, 0)
    new_semi = (curr_semi + semitones) % 12
    
    transposed = ROOT_NAMES[new_semi]
    if prefer_flats and transposed in ENHARMONIC_SHARP_TO_FLAT:
        transposed = ENHARMONIC_SHARP_TO_FLAT[transposed]
        
    return transposed


def transpose_chord(chord: ChordPrediction, semitones: int, prefer_flats: bool = False) -> ChordPrediction:
    """Transposes root and bass of a ChordPrediction, preserving quality and inversion."""
    if chord.root in ['N', 'X'] or semitones == 0:
        return chord.model_copy()

    new_root = transpose_note(chord.root, semitones, prefer_flats)
    new_bass = transpose_note(chord.bass, semitones, prefer_flats)
    
    new_inversion = chord.inversion
    if new_bass != new_root:
        new_inversion = calculate_inversion(new_root, chord.quality, new_bass)
    else:
        new_inversion = 0

    qual_display = QUALITY_DISPLAY_MAP.get(chord.quality, chord.quality)
    new_display = f"{new_root}{qual_display}"
    if new_bass != new_root:
        new_display = f"{new_display}/{new_bass}"

    # Also transpose alternatives
    new_alts = []
    for alt in chord.alternatives:
        from backend.chord.vocabulary import parse_chord_string
        r, q, b, inv, disp = parse_chord_string(alt.chord)
        tr_r = transpose_note(r, semitones, prefer_flats)
        tr_b = transpose_note(b, semitones, prefer_flats)
        tr_q_disp = QUALITY_DISPLAY_MAP.get(q, q)
        tr_disp = f"{tr_r}{tr_q_disp}"
        if tr_b != tr_r:
            tr_disp = f"{tr_disp}/{tr_b}"
        new_alts.append(alt.model_copy(update={"chord": tr_disp}))

    return chord.model_copy(update={
        "root": new_root,
        "bass": new_bass,
        "inversion": new_inversion,
        "display": new_display,
        "alternatives": new_alts
    })


def transpose_song(analysis: SongAnalysis, semitones: int) -> SongAnalysis:
    """Transposes all chords, bars, sections, and the key signature of a SongAnalysis."""
    if semitones == 0:
        return analysis

    # Determine if target key is a flat key
    target_tonic = transpose_note(analysis.key.tonic, semitones, prefer_flats=False)
    test_key_str = f"{target_tonic}" + ("m" if analysis.key.mode == "minor" else "")
    prefer_flats = test_key_str in FLAT_KEYS
    target_tonic = transpose_note(analysis.key.tonic, semitones, prefer_flats=prefer_flats)

    # Transpose key
    new_key_display = f"{target_tonic} {analysis.key.mode.capitalize()}"
    new_key = analysis.key.model_copy(update={
        "tonic": target_tonic,
        "display": new_key_display
    })

    # Transpose flat chords list
    transposed_chords = [transpose_chord(c, semitones, prefer_flats) for c in analysis.chords]

    # Transpose sections and nested bars
    transposed_sections = []
    for sec in analysis.sections:
        transposed_bars = []
        for b in sec.bars:
            bar_chords = [transpose_chord(bc, semitones, prefer_flats) for bc in b.chords]
            if len(bar_chords) == 1:
                new_display = bar_chords[0].display
            elif len(bar_chords) == 2:
                new_display = f"{bar_chords[0].display}   {bar_chords[1].display}"
            else:
                new_display = "  ".join(c.display for c in bar_chords)

            transposed_bars.append(b.model_copy(update={
                "chords": bar_chords,
                "display": new_display
            }))
            
        transposed_sections.append(sec.model_copy(update={"bars": transposed_bars}))

    return analysis.model_copy(update={
        "key": new_key,
        "chords": transposed_chords,
        "sections": transposed_sections,
        "transpose_semitones": analysis.transpose_semitones + semitones
    })
