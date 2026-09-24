"""
Temporal smoothing and de-jittering module.
Filters out isolated single-beat classification glitches without eliminating genuine musical changes.
"""

from typing import List
import numpy as np

from backend.models.schemas import ChordPrediction


def smooth_chord_sequence(chords: List[ChordPrediction]) -> List[ChordPrediction]:
    """
    Applies musical temporal smoothing to beat-level chord sequence:
    1. Removes momentary 1-beat flickers (e.g., A -> D -> A where D is low confidence)
    2. Preserves genuine harmonic rhythm (half-bar changes, intentional fast changes)
    3. Merges contiguous matching chords into single sustained predictions
    """
    if len(chords) < 3:
        return chords

    cleaned = list(chords)
    
    # Pass 1: Eliminate transient single-beat blips between identical surrounding chords
    for i in range(1, len(cleaned) - 1):
        prev_c = cleaned[i - 1]
        curr_c = cleaned[i]
        next_c = cleaned[i + 1]

        # If surrounded by the same chord and current chord is low confidence or short
        if prev_c.display == next_c.display and curr_c.display != prev_c.display:
            if curr_c.confidence < 0.72 or curr_c.duration < 0.6:
                # Replace with surrounding chord
                cleaned[i] = ChordPrediction(
                    root=prev_c.root,
                    quality=prev_c.quality,
                    bass=prev_c.bass,
                    inversion=prev_c.inversion,
                    display=prev_c.display,
                    start_time=curr_c.start_time,
                    end_time=curr_c.end_time,
                    duration=curr_c.duration,
                    confidence=round((prev_c.confidence + next_c.confidence) / 2.0, 2),
                    needs_review=False,
                    alternatives=prev_c.alternatives
                )

    # Pass 2: Merge adjacent matching chords into sustained events
    merged: List[ChordPrediction] = []
    current = cleaned[0]
    curr_start = current.start_time
    curr_end = current.end_time
    confs = [current.confidence]

    for c in cleaned[1:]:
        if c.display == current.display:
            curr_end = c.end_time
            confs.append(c.confidence)
        else:
            merged.append(ChordPrediction(
                root=current.root,
                quality=current.quality,
                bass=current.bass,
                inversion=current.inversion,
                display=current.display,
                start_time=round(curr_start, 3),
                end_time=round(curr_end, 3),
                duration=round(curr_end - curr_start, 3),
                confidence=round(float(np.mean(confs)), 2),
                needs_review=(float(np.mean(confs)) < 0.65 and current.display != 'N'),
                alternatives=current.alternatives
            ))
            current = c
            curr_start = c.start_time
            curr_end = c.end_time
            confs = [c.confidence]

    # Append trailing event
    merged.append(ChordPrediction(
        root=current.root,
        quality=current.quality,
        bass=current.bass,
        inversion=current.inversion,
        display=current.display,
        start_time=round(curr_start, 3),
        end_time=round(curr_end, 3),
        duration=round(curr_end - curr_start, 3),
        confidence=round(float(np.mean(confs)), 2),
        needs_review=(float(np.mean(confs)) < 0.65 and current.display != 'N'),
        alternatives=current.alternatives
    ))

    return merged
