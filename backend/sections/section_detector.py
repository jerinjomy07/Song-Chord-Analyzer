"""
Musical Section Detection and Structural Form Analysis module.
Segments song into neutral structural labels (INTRO, SECTION A, SECTION B, OUTRO)
and identifies repeated harmonic structures without forcing false semantic labels.
"""

from typing import List, Dict, Tuple, Optional
import numpy as np
import librosa
from pathlib import Path
import soundfile as sf

from backend.models.schemas import MusicalSection, Bar


class SectionDetector:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def detect_sections(
        self,
        audio_path: Path,
        bars: List[Bar],
        total_duration: float
    ) -> List[MusicalSection]:
        """
        Segments the song into musical sections aligned with bars,
        using neutral structural labels (INTRO, SECTION A, SECTION B, OUTRO)
        and linking repeated harmonic progressions.
        """
        if not bars:
            return [
                MusicalSection(
                    section_id="sec_1",
                    name="SECTION A",
                    start_time=0.0,
                    end_time=total_duration,
                    start_bar=1,
                    end_bar=1,
                    bars=[]
                )
            ]

        total_bars = len(bars)
        # Standard pop/worship structure: 8 bars per section (or 4 bars if total bars < 24)
        bars_per_sec = 8 if total_bars >= 24 else 4
        
        raw_sections: List[Tuple[int, int]] = []
        for b_start in range(0, total_bars, bars_per_sec):
            b_end = min(b_start + bars_per_sec, total_bars)
            raw_sections.append((b_start, b_end))

        # Audio energy analysis for intro / outro
        y, sr = sf.read(str(audio_path))
        if y.ndim > 1:
            y = np.mean(y, axis=1)

        rms = librosa.feature.rms(y=y, hop_length=2048)[0]
        rms_times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=2048)

        # Extract chord fingerprints and energies per section
        section_fingerprints = []
        section_energies = []

        for b_start, b_end in raw_sections:
            sec_bars = bars[b_start:b_end]
            sec_start_t = sec_bars[0].start_time
            sec_end_t = sec_bars[-1].end_time

            # Chord progression string (ignoring N)
            chords_in_sec = [c.display for b in sec_bars for c in b.chords if c.display != 'N']
            section_fingerprints.append(chords_in_sec)

            mask = (rms_times >= sec_start_t) & (rms_times <= sec_end_t)
            avg_energy = float(np.mean(rms[mask])) if np.any(mask) else 0.0
            section_energies.append(avg_energy)

        # Repetition clustering
        num_sections = len(raw_sections)
        clusters = [-1] * num_sections
        cluster_id_counter = 0

        for i in range(num_sections):
            if clusters[i] != -1:
                continue
            clusters[i] = cluster_id_counter
            for j in range(i + 1, num_sections):
                if clusters[j] != -1:
                    continue
                sim = self._chord_similarity(section_fingerprints[i], section_fingerprints[j])
                if sim >= 0.70:
                    clusters[j] = cluster_id_counter
            cluster_id_counter += 1

        # Neutral Structural Labeling (Requirement 10)
        # Uses INTRO, SECTION A, SECTION B, SECTION C, ... and OUTRO
        section_letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
        cluster_to_letter: Dict[int, str] = {}
        letter_idx = 0

        median_energy = float(np.median(section_energies)) if section_energies else 0.0
        sections: List[MusicalSection] = []

        for idx, (b_start, b_end) in enumerate(raw_sections):
            sec_id = f"sec_{idx + 1}"
            c_id = clusters[idx]
            sec_bars = bars[b_start:b_end]
            sec_start_t = sec_bars[0].start_time
            sec_end_t = sec_bars[-1].end_time
            energy = section_energies[idx]
            is_silent_or_sparse = (not section_fingerprints[idx] or all(c == 'N' for c in section_fingerprints[idx]))

            # Check if this cluster has been seen before
            is_repeat = (clusters.count(c_id) > 1 and clusters.index(c_id) < idx)
            first_idx = clusters.index(c_id)
            repeat_of = f"sec_{first_idx + 1}" if is_repeat else None

            # Label assignment
            if idx == 0 and (is_silent_or_sparse or energy < median_energy * 0.75):
                name = "INTRO"
            elif idx == num_sections - 1 and (is_silent_or_sparse or energy < median_energy * 0.75):
                name = "OUTRO"
            else:
                if c_id not in cluster_to_letter:
                    assigned_letter = section_letters[letter_idx % len(section_letters)]
                    letter_idx += 1
                    cluster_to_letter[c_id] = assigned_letter

                base_letter = cluster_to_letter[c_id]
                if is_repeat:
                    name = f"SECTION {base_letter} (Repeat)"
                else:
                    name = f"SECTION {base_letter}"

            sections.append(MusicalSection(
                section_id=sec_id,
                name=name,
                start_time=round(sec_start_t, 3),
                end_time=round(sec_end_t, 3),
                start_bar=b_start + 1,
                end_bar=b_end,
                bars=sec_bars,
                is_repeated=is_repeat,
                repeat_of_section_id=repeat_of
            ))

        return sections

    def _chord_similarity(self, list_a: List[str], list_b: List[str]) -> float:
        """Computes overlap similarity between two chord sequences."""
        if not list_a and not list_b:
            return 1.0
        if not list_a or not list_b:
            return 0.0

        set_a = set(list_a)
        set_b = set(list_b)
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / float(union) if union > 0 else 0.0
