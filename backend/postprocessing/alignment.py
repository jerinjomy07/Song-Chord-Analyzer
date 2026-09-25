"""
Musical Bar alignment and Chord Sheet grid construction module.
Maps beat-synchronous chord predictions into clean musical measure/bar containers.
Eliminates boundary spillover artifacts, supports pickup bars (anacrusis),
and guarantees musician-standard bar representation across 2/4, 3/4, 4/4, 6/8, 7/8, and 12/8.
"""

from typing import List, Tuple, Dict, Any, Optional
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
        Respects downbeat timestamps and pickup bars (anacrusis).
        Supports 2/4, 3/4, 4/4, 6/8, 7/8, and 12/8.
        """
        beats = beat_grid.beats
        downbeats = beat_grid.downbeats
        pickup_beats = getattr(beat_grid, "pickup_beats", 0)
        beats_per_bar = meter.numerator if meter and meter.numerator > 0 else 4

        if not beats or len(beats) < 2 or not beat_chords:
            return []

        # Map beat intervals to chords
        mapped_beat_chords: List[ChordPrediction] = []
        for i in range(len(beats) - 1):
            start_t = beats[i]
            end_t = beats[i + 1]
            mid_t = (start_t + end_t) / 2.0

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

        # Fallback downbeats if empty
        if not downbeats or len(downbeats) < 2:
            step = beats_per_bar
            downbeats = [beats[i] for i in range(0, len(beats), step)]

        bars: List[Bar] = []
        bar_boundaries: List[List[float]] = []

        # 1. Pickup Bar (Anacrusis) if beats exist before the first downbeat
        first_downbeat = downbeats[0]
        pickup_slice = [c for c in mapped_beat_chords if c.end_time <= first_downbeat + 0.05]

        if pickup_slice and len(pickup_slice) < beats_per_bar:
            p_start = pickup_slice[0].start_time
            p_end = pickup_slice[-1].end_time
            p_display = "  ".join(dict.fromkeys([c.display for c in pickup_slice]))
            for b_i, c in enumerate(pickup_slice):
                c.bar_position = 0
                c.beat_position = b_i + 1
                c.beat = b_i + 1
                c.beat_duration = 1.0

            pickup_bar = Bar(
                bar_number=0,
                start_time=round(p_start, 3),
                end_time=round(p_end, 3),
                beats=len(pickup_slice),
                chords=pickup_slice,
                display=p_display,
                time_signature=meter.display if meter else f"{beats_per_bar}/4"
            )
            bars.append(pickup_bar)
            bar_boundaries.append([pickup_bar.start_time, pickup_bar.end_time])

        # 2. Main bars partitioned strictly by consecutive downbeats
        for d_idx in range(len(downbeats) - 1):
            bar_num = len(bars) if (bars and bars[0].bar_number == 0) else d_idx + 1
            b_start = downbeats[d_idx]
            b_end = downbeats[d_idx + 1]

            # Collect beat chords within this bar interval
            bar_slice = [
                c.model_copy() for c in mapped_beat_chords
                if c.start_time >= b_start - 0.05 and c.end_time <= b_end + 0.05
            ]

            if not bar_slice:
                # Synthetic fallback chord if no slice found
                fallback = self._find_closest_chord(mapped_beat_chords, (b_start + b_end) / 2.0).model_copy()
                fallback.start_time = round(b_start, 3)
                fallback.end_time = round(b_end, 3)
                fallback.duration = round(b_end - b_start, 3)
                fallback.bar_position = bar_num
                fallback.beat_position = 1
                fallback.beat = 1
                fallback.beat_duration = float(beats_per_bar)
                bar_slice = [fallback]

            # Clean intra-bar transient 'N' when the bar contains real music
            has_music = any(c.display != "N" for c in bar_slice)
            cleaned_slice = []
            if has_music:
                last_valid = next(c for c in bar_slice if c.display != "N")
                for c in bar_slice:
                    if c.display == "N":
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
                # 1 chord held across the entire measure
                c = bar_slice[0].model_copy()
                c.start_time = round(b_start, 3)
                c.end_time = round(b_end, 3)
                c.duration = round(b_end - b_start, 3)
                c.bar_position = bar_num
                c.beat_position = 1
                c.beat = 1
                c.beat_duration = float(beats_per_bar)
                final_bar_chords = [c]
                bar_display = c.display

            elif beats_per_bar == 4 and len(bar_slice) >= 4:
                # 4/4 Harmonic Rhythm
                is_walkdown = (len(unique_labels) == 4 and all(c.confidence >= 0.58 for c in bar_slice))
                if is_walkdown:
                    final_bar_chords = []
                    display_parts = []
                    for b_i, bc in enumerate(bar_slice[:4]):
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
                    h1_chord = bar_slice[0]
                    if bar_slice[0].display != bar_slice[1].display and bar_slice[1].confidence > bar_slice[0].confidence * 1.3:
                        h1_chord = bar_slice[1]

                    h2_chord = bar_slice[2]
                    if bar_slice[2].display != bar_slice[3].display and bar_slice[3].confidence > bar_slice[2].confidence * 1.3:
                        h2_chord = bar_slice[3]

                    if h1_chord.display == h2_chord.display:
                        c = h1_chord.model_copy()
                        c.start_time = round(b_start, 3)
                        c.end_time = round(b_end, 3)
                        c.duration = round(b_end - b_start, 3)
                        c.bar_position = bar_num
                        c.beat_position = 1
                        c.beat = 1
                        c.beat_duration = 4.0
                        final_bar_chords = [c]
                        bar_display = c.display
                    else:
                        c1 = h1_chord.model_copy()
                        c1.start_time = round(b_start, 3)
                        c1.end_time = round(bar_slice[1].end_time, 3)
                        c1.duration = round(c1.end_time - c1.start_time, 3)
                        c1.bar_position = bar_num
                        c1.beat_position = 1
                        c1.beat = 1
                        c1.beat_duration = 2.0

                        c2 = h2_chord.model_copy()
                        c2.start_time = round(bar_slice[2].start_time, 3)
                        c2.end_time = round(b_end, 3)
                        c2.duration = round(c2.end_time - c2.start_time, 3)
                        c2.bar_position = bar_num
                        c2.beat_position = 3
                        c2.beat = 3
                        c2.beat_duration = 2.0

                        final_bar_chords = [c1, c2]
                        bar_display = f"{c1.display}   {c2.display}"

            elif beats_per_bar == 3 and len(bar_slice) >= 3:
                # 3/4 Harmonic Rhythm
                counts = {c: chord_labels.count(c) for c in unique_labels}
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= 2:
                    idx = chord_labels.index(dominant)
                    c = bar_slice[idx].model_copy()
                    c.start_time = round(b_start, 3)
                    c.end_time = round(b_end, 3)
                    c.duration = round(b_end - b_start, 3)
                    c.bar_position = bar_num
                    c.beat_position = 1
                    c.beat = 1
                    c.beat_duration = 3.0
                    final_bar_chords = [c]
                    bar_display = c.display
                else:
                    final_bar_chords = []
                    display_parts = []
                    for b_i, bc in enumerate(bar_slice[:3]):
                        c = bc.model_copy()
                        c.bar_position = bar_num
                        c.beat_position = b_i + 1
                        c.beat = b_i + 1
                        c.beat_duration = 1.0
                        final_bar_chords.append(c)
                        display_parts.append(c.display)
                    bar_display = "  ".join(display_parts)

            else:
                # General grouping for 2/4, 6/8, 7/8, 12/8
                counts = {c: chord_labels.count(c) for c in unique_labels}
                dominant = max(counts, key=counts.get)
                if counts[dominant] >= max(1, len(bar_slice) // 2 + 1):
                    idx = chord_labels.index(dominant)
                    c = bar_slice[idx].model_copy()
                    c.start_time = round(b_start, 3)
                    c.end_time = round(b_end, 3)
                    c.duration = round(b_end - b_start, 3)
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

            current_bar = Bar(
                bar_number=bar_num,
                start_time=round(b_start, 3),
                end_time=round(b_end, 3),
                beats=beats_per_bar,
                chords=final_bar_chords,
                display=bar_display,
                time_signature=meter.display if meter else f"{beats_per_bar}/4"
            )
            bars.append(current_bar)
            bar_boundaries.append([current_bar.start_time, current_bar.end_time])

        # Save bar boundaries in beat_grid
        beat_grid.bar_boundaries = bar_boundaries

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
