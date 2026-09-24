"""
Musical Bar alignment and Chord Sheet grid construction module.
Maps beat-synchronous chord predictions into clean musical measure/bar containers.
Eliminates boundary spillover artifacts and guarantees musician-standard bar representation.
"""

from typing import List, Tuple, Dict, Any
from backend.models.schemas import Bar, ChordPrediction, BeatGrid, MeterAnalysis


class BarAligner:
    def __init__(self):
        pass

    def align_to_bars(
        self,
        beat_chords: List[ChordPrediction],
        beat_grid: BeatGrid,
        meter: MeterAnalysis
    ) -> List[Bar]:
        """
        Organizes beat-level chords into structured musical bars.
        Supports 1 chord/bar, 2 chords/bar (half-bar changes), and 4 chords/bar.
        Eliminates duplicate boundary slivers.
        """
        beats = beat_grid.beats
        beats_per_bar = meter.numerator if meter and meter.numerator > 0 else 4

        if not beats or len(beats) < 2 or not beat_chords:
            return []

        # Ensure we have a chord per beat interval
        # If beat_chords matches beats length, map directly; otherwise align by timestamps
        mapped_beat_chords: List[ChordPrediction] = []
        for i in range(len(beats) - 1):
            start_t = beats[i]
            end_t = beats[i + 1]
            mid_t = (start_t + end_t) / 2.0

            # Find matching chord from beat_chords
            matched = None
            for c in beat_chords:
                if c.start_time <= mid_t <= c.end_time:
                    matched = c
                    break
            if not matched:
                matched = self._find_closest_chord(beat_chords, mid_t)
            
            c_copy = matched.model_copy()
            c_copy.start_time = round(start_t, 3)
            c_copy.end_time = round(end_t, 3)
            c_copy.duration = round(end_t - start_t, 3)
            mapped_beat_chords.append(c_copy)

        num_bars = len(mapped_beat_chords) // beats_per_bar
        bars: List[Bar] = []

        for b_idx in range(num_bars):
            bar_num = b_idx + 1
            bar_slice = mapped_beat_chords[b_idx * beats_per_bar : (b_idx + 1) * beats_per_bar]
            bar_start = bar_slice[0].start_time
            bar_end = bar_slice[-1].end_time

            chord_labels = [c.display for c in bar_slice]
            unique_labels = list(dict.fromkeys(chord_labels))

            final_bar_chords: List[ChordPrediction] = []
            bar_display = ""

            # 1. Clean intra-bar transient 'N' when the bar contains real music
            has_music = any(c.display != 'N' for c in bar_slice)
            cleaned_slice = []
            if has_music:
                last_valid = next(c for c in bar_slice if c.display != 'N')
                for c in bar_slice:
                    if c.display == 'N':
                        c_clean = last_valid.model_copy()
                        c_clean.start_time = c.start_time
                        c_clean.end_time = c.end_time
                        c_clean.duration = c.duration
                        cleaned_slice.append(c_clean)
                    else:
                        cleaned_slice.append(c)
                        last_valid = c
            else:
                cleaned_slice = list(bar_slice)

            bar_slice = cleaned_slice
            chord_labels = [c.display for c in bar_slice]
            unique_labels = list(dict.fromkeys(chord_labels))

            final_bar_chords: List[ChordPrediction] = []
            bar_display = ""

            if not has_music or len(unique_labels) == 1:
                # 1 chord per bar (held across all beats, or silence)
                c = bar_slice[0].model_copy()
                c.start_time = bar_start
                c.end_time = bar_end
                c.duration = round(bar_end - bar_start, 3)
                c.bar_position = bar_num
                c.beat_position = 1
                c.beat = 1
                c.beat_duration = float(beats_per_bar)
                final_bar_chords = [c]
                bar_display = c.display

            elif beats_per_bar == 4:
                # 4/4 Musical Harmonic Rhythm:
                # Check for genuine 4-chord walkdown (e.g. D - Cm/Eb - F - Gm)
                is_walkdown = (len(unique_labels) == 4 and all(c.confidence >= 0.58 for c in bar_slice))

                if is_walkdown:
                    final_bar_chords = []
                    display_parts = []
                    for b_i, bc in enumerate(bar_slice):
                        c = bc.model_copy()
                        c.bar_position = bar_num
                        c.beat_position = b_i + 1
                        c.beat = b_i + 1
                        c.beat_duration = 1.0
                        final_bar_chords.append(c)
                        display_parts.append(c.display)
                    bar_display = "  ".join(display_parts)
                else:
                    # Half-bar grouping: Half 1 (Beats 1-2) and Half 2 (Beats 3-4)
                    # For Half 1: downbeat priority (beat 0) unless beat 1 is identical or significantly higher confidence
                    h1_chord = bar_slice[0]
                    if bar_slice[0].display != bar_slice[1].display and bar_slice[1].confidence > bar_slice[0].confidence * 1.3:
                        h1_chord = bar_slice[1]

                    # For Half 2: beat 3 priority (beat 2) unless beat 4 is identical or significantly higher confidence
                    h2_chord = bar_slice[2]
                    if bar_slice[2].display != bar_slice[3].display and bar_slice[3].confidence > bar_slice[2].confidence * 1.3:
                        h2_chord = bar_slice[3]

                    if h1_chord.display == h2_chord.display:
                        # 1 single chord held for the entire bar
                        c = h1_chord.model_copy()
                        c.start_time = bar_start
                        c.end_time = bar_end
                        c.duration = round(bar_end - bar_start, 3)
                        c.bar_position = bar_num
                        c.beat_position = 1
                        c.beat = 1
                        c.beat_duration = 4.0
                        final_bar_chords = [c]
                        bar_display = c.display
                    else:
                        # 2 chords: Half-bar change on beat 1 and beat 3
                        c1 = h1_chord.model_copy()
                        c1.start_time = bar_start
                        c1.end_time = bar_slice[1].end_time
                        c1.duration = round(c1.end_time - c1.start_time, 3)
                        c1.bar_position = bar_num
                        c1.beat_position = 1
                        c1.beat = 1
                        c1.beat_duration = 2.0

                        c2 = h2_chord.model_copy()
                        c2.start_time = bar_slice[2].start_time
                        c2.end_time = bar_end
                        c2.duration = round(c2.end_time - c2.start_time, 3)
                        c2.bar_position = bar_num
                        c2.beat_position = 3
                        c2.beat = 3
                        c2.beat_duration = 2.0

                        final_bar_chords = [c1, c2]
                        bar_display = f"{c1.display}   {c2.display}"

            else:
                # Other meters (e.g. 3/4): dominant chord or per-beat
                counts = {c: chord_labels.count(c) for c in unique_labels}
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= 2:
                    idx = chord_labels.index(dominant)
                    c = bar_slice[idx].model_copy()
                    c.start_time = bar_start
                    c.end_time = bar_end
                    c.duration = round(bar_end - bar_start, 3)
                    c.bar_position = bar_num
                    c.beat_position = 1
                    c.beat = 1
                    c.beat_duration = float(beats_per_bar)
                    final_bar_chords = [c]
                    bar_display = c.display
                else:
                    final_bar_chords = []
                    display_parts = []
                    for b_i, bc in enumerate(bar_slice):
                        c = bc.model_copy()
                        c.bar_position = bar_num
                        c.beat_position = b_i + 1
                        c.beat = b_i + 1
                        c.beat_duration = 1.0
                        final_bar_chords.append(c)
                        display_parts.append(c.display)
                    bar_display = "  ".join(display_parts)

            bars.append(Bar(
                bar_number=bar_num,
                start_time=round(bar_start, 3),
                end_time=round(bar_end, 3),
                beats=beats_per_bar,
                chords=final_bar_chords,
                display=bar_display,
                time_signature=meter.display if meter else f"{beats_per_bar}/4"
            ))

        return bars

    def _find_closest_chord(self, chords: List[ChordPrediction], t: float) -> ChordPrediction:
        closest = chords[0]
        min_dist = abs((chords[0].start_time + chords[0].end_time) / 2.0 - t)
        for c in chords:
            dist = abs((c.start_time + c.end_time) / 2.0 - t)
            if dist < min_dist:
                min_dist = dist
                closest = c
        return closest
