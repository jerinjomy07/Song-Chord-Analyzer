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
            pickup_clean = self._clean_transient_noise(pickup_slice)
            p_chords = self._group_consecutive_chords(
                pickup_clean,
                bar_num=0,
                b_start=p_start,
                b_end=p_end,
                beats_per_bar=len(pickup_slice)
            )
            p_display = "   ".join([c.display for c in p_chords])
            pickup_bar = Bar(
                bar_number=0,
                start_time=round(p_start, 3),
                end_time=round(p_end, 3),
                beats=len(pickup_slice),
                chords=p_chords,
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

            cleaned_slice = self._clean_transient_noise(cleaned_slice)
            final_bar_chords = self._group_consecutive_chords(
                cleaned_slice,
                bar_num=bar_num,
                b_start=b_start,
                b_end=b_end,
                beats_per_bar=beats_per_bar
            )
            bar_display = "   ".join([c.display for c in final_bar_chords if c.display != 'N']) or "N"

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

    def _clean_transient_noise(self, bar_slice: List[ChordPrediction]) -> List[ChordPrediction]:
        """Filters momentary 1-beat classification flickers inside a single measure."""
        if len(bar_slice) < 3:
            return bar_slice

        cleaned = [c.model_copy() for c in bar_slice]

        # 1. 1-beat blip surrounded by identical chords: A -> D(low conf) -> A
        for i in range(1, len(cleaned) - 1):
            if cleaned[i - 1].display == cleaned[i + 1].display and cleaned[i].confidence < 0.65:
                cleaned[i] = cleaned[i - 1].model_copy()

        # 2. 1-beat edge blips (< 0.35 conf) when adjacent chord has strong confidence
        if len(cleaned) >= 3:
            if cleaned[-1].confidence < 0.35 and cleaned[-2].confidence >= 0.50:
                cleaned[-1] = cleaned[-2].model_copy()
            if cleaned[0].confidence < 0.35 and cleaned[1].confidence >= 0.50:
                cleaned[0] = cleaned[1].model_copy()

        return cleaned

    def _group_consecutive_chords(
        self,
        bar_slice: List[ChordPrediction],
        bar_num: int,
        b_start: float,
        b_end: float,
        beats_per_bar: int
    ) -> List[ChordPrediction]:
        """
        Run-length merges consecutive identical chords within a measure into single sustained chord events.
        Guarantees no chord is ever repeated on consecutive pulses.
        """
        if not bar_slice:
            return []

        # If all chords are identical or no music, return single chord held for entire measure
        unique_displays = list(dict.fromkeys([c.display for c in bar_slice]))
        if len(unique_displays) == 1:
            c = bar_slice[0].model_copy()
            c.start_time = round(b_start, 3)
            c.end_time = round(b_end, 3)
            c.duration = round(b_end - b_start, 3)
            c.bar_position = bar_num
            c.beat_position = 1
            c.beat = 1
            c.beat_duration = float(beats_per_bar)
            return [c]

        groups: List[ChordPrediction] = []
        curr = bar_slice[0]
        st_b, end_b = 1, 1
        confs = [curr.confidence]

        for i in range(1, len(bar_slice)):
            c = bar_slice[i]
            if c.display == curr.display:
                end_b = i + 1
                confs.append(c.confidence)
            else:
                g = curr.model_copy()
                g.start_time = round(bar_slice[st_b - 1].start_time, 3)
                g.end_time = round(bar_slice[end_b - 1].end_time, 3)
                g.duration = round(g.end_time - g.start_time, 3)
                g.bar_position = bar_num
                g.beat_position = st_b
                g.beat = st_b
                g.beat_duration = float(end_b - st_b + 1)
                g.confidence = round(float(sum(confs) / len(confs)), 2)
                groups.append(g)

                curr = c
                st_b, end_b = i + 1, i + 1
                confs = [c.confidence]

        # Final group
        g = curr.model_copy()
        g.start_time = round(bar_slice[st_b - 1].start_time, 3)
        g.end_time = round(bar_slice[end_b - 1].end_time, 3)
        g.duration = round(g.end_time - g.start_time, 3)
        g.bar_position = bar_num
        g.beat_position = st_b
        g.beat = st_b
        g.beat_duration = float(end_b - st_b + 1)
        g.confidence = round(float(sum(confs) / len(confs)), 2)
        groups.append(g)

        # Simplify if there are more than 4 chords in a single measure
        groups = self._simplify_bar_chords(groups, max_chords=4)

        # Boundary snap
        groups[0].start_time = round(b_start, 3)
        groups[-1].end_time = round(b_end, 3)
        groups[-1].duration = round(groups[-1].end_time - groups[-1].start_time, 3)

        # Ensure total beat_duration matches beats_per_bar
        total_beats = sum(grp.beat_duration for grp in groups)
        if total_beats != beats_per_bar and total_beats > 0:
            ratio = float(beats_per_bar) / total_beats
            for grp in groups:
                grp.beat_duration = round(grp.beat_duration * ratio, 2)

        return groups

    def _simplify_bar_chords(self, groups: List[ChordPrediction], max_chords: int = 4) -> List[ChordPrediction]:
        """
        Simplifies dense measure clusters to at most max_chords for professional lead-sheet readability.
        Prefers merging same-root bass movements or low-confidence 1-beat flickers into stronger neighbors.
        """
        while len(groups) > max_chords:
            # 1. Try to merge adjacent chords that share the same root
            merged = False
            for i in range(len(groups) - 1):
                if groups[i].root == groups[i + 1].root:
                    if groups[i].confidence >= groups[i + 1].confidence:
                        groups[i].end_time = groups[i + 1].end_time
                        groups[i].duration = round(groups[i].end_time - groups[i].start_time, 3)
                        groups[i].beat_duration += groups[i + 1].beat_duration
                    else:
                        groups[i + 1].start_time = groups[i].start_time
                        groups[i + 1].duration = round(groups[i + 1].end_time - groups[i + 1].start_time, 3)
                        groups[i + 1].beat = groups[i].beat
                        groups[i + 1].beat_position = groups[i].beat_position
                        groups[i + 1].beat_duration += groups[i].beat_duration
                        groups[i] = groups[i + 1]
                    del groups[i + 1]
                    merged = True
                    break

            if not merged:
                # 2. Merge the shortest/lowest-confidence chord into its adjacent stronger neighbor
                candidates = [i for i in range(len(groups)) if groups[i].beat_duration <= 1.0]
                if not candidates:
                    candidates = list(range(len(groups)))
                worst_idx = min(candidates, key=lambda idx: groups[idx].confidence)
                if worst_idx > 0 and (worst_idx == len(groups) - 1 or groups[worst_idx - 1].confidence >= groups[worst_idx + 1].confidence):
                    target_idx = worst_idx - 1
                    groups[target_idx].end_time = groups[worst_idx].end_time
                    groups[target_idx].duration = round(groups[target_idx].end_time - groups[target_idx].start_time, 3)
                    groups[target_idx].beat_duration += groups[worst_idx].beat_duration
                    del groups[worst_idx]
                else:
                    target_idx = worst_idx + 1
                    groups[target_idx].start_time = groups[worst_idx].start_time
                    groups[target_idx].duration = round(groups[target_idx].end_time - groups[target_idx].start_time, 3)
                    groups[target_idx].beat = groups[worst_idx].beat
                    groups[target_idx].beat_position = groups[worst_idx].beat_position
                    groups[target_idx].beat_duration += groups[worst_idx].beat_duration
                    del groups[worst_idx]

        return groups

    def _find_closest_chord(self, chords: List[ChordPrediction], t: float) -> ChordPrediction:
        closest = chords[0]
        min_dist = abs((chords[0].start_time + chords[0].end_time) / 2.0 - t)
        for c in chords:
            dist = abs((c.start_time + c.end_time) / 2.0 - t)
            if dist < min_dist:
                min_dist = dist
                closest = c
        return closest
