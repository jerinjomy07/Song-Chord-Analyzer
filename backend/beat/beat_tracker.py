"""
Beat and tempo tracking module.
Automatically detects BPM, beat positions, downbeats, and bar boundaries
with comprehensive multi-hypothesis tempo estimation, onset density disambiguation,
and compound meter support.
"""

from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any
import numpy as np
import librosa
import soundfile as sf

from backend.models.schemas import BeatGrid, TempoAnalysis


class BeatTracker:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def track_beats(
        self,
        audio_path: Optional[Path] = None,
        meter_numerator: int = 4,
        y: Optional[np.ndarray] = None,
        sr: Optional[int] = None
    ) -> Tuple[BeatGrid, TempoAnalysis]:
        """
        Detects BPM, multi-hypothesis tempo candidates, beat timestamps, and initial downbeats.
        Supports compound meters, dotted-quarter pulses, and half/double tempo disambiguation.
        """
        if y is None or sr is None:
            if audio_path is None:
                raise ValueError("Either audio_path or (y, sr) must be provided")
            y, sr = sf.read(str(audio_path))
            if y.ndim > 1:
                y = np.mean(y, axis=1)

        # Compute onset strength envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=512)

        # 1. Multi-hypothesis tempo analysis
        tempo_info, beat_frames = self._estimate_tempo_multi_hypothesis(y, sr, onset_env, hop_length=512)
        bpm = tempo_info.bpm

        # Convert beat frames to seconds
        beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=512).tolist()

        if len(beat_times) < 2:
            duration = len(y) / sr
            sec_per_beat = 60.0 / max(30.0, bpm)
            beat_times = list(np.arange(0, duration, sec_per_beat))
            beat_frames = librosa.time_to_frames(beat_times, sr=sr, hop_length=512)

        # Downbeat detection: Initial cyclic offset on onset energy
        downbeats = self._detect_downbeats(onset_env, beat_frames, beat_times, meter_numerator, sr)

        beat_grid = BeatGrid(
            bpm=bpm,
            beats=beat_times,
            downbeats=downbeats,
            pickup_beats=0,
            bar_boundaries=[]
        )

        return beat_grid, tempo_info

    def _estimate_tempo_multi_hypothesis(
        self,
        y: np.ndarray,
        sr: int,
        onset_env: np.ndarray,
        hop_length: int = 512
    ) -> Tuple[TempoAnalysis, np.ndarray]:
        """
        Evaluates candidate tempi using tempogram peaks, autocorrelation harmonics,
        onset density (events per beat), and inter-beat interval regularity.
        """
        duration = len(y) / sr
        # Onset event detection for tactus density estimation
        onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length, units="time")
        onset_rate = len(onsets) / max(1.0, duration)

        # 1. Tempogram
        tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr, hop_length=hop_length)
        mean_tg = np.mean(tg, axis=1)
        tempi = librosa.tempo_frequencies(tg.shape[0], sr=sr, hop_length=hop_length)

        # 2. Continuous onset autocorrelation
        max_lag = int(5.5 * sr / hop_length)
        ac = librosa.autocorrelate(onset_env, max_size=max_lag)
        ac_norm = ac / (ac[0] + 1e-8)
        times = np.arange(len(ac_norm)) * (hop_length / sr)

        # Fundamental subdivision pulse tau_e
        sub_peaks = []
        for i in range(2, len(ac_norm) - 2):
            if ac_norm[i] > ac_norm[i - 1] and ac_norm[i] > ac_norm[i + 1] and 0.16 <= times[i] <= 0.46:
                sub_peaks.append((float(times[i]), float(ac_norm[i])))
        sub_peaks.sort(key=lambda x: x[1], reverse=True)
        tau_e = sub_peaks[0][0] if sub_peaks else 0.35

        mean_onset = float(np.mean(onset_env)) + 1e-8

        # Extract local peaks in tempogram
        raw_candidates: List[float] = [
            round(60.0 / (2.0 * tau_e), 1),
            round(60.0 / (3.0 * tau_e), 1),
            round(60.0 / tau_e, 1)
        ]
        for i in range(1, len(mean_tg) - 1):
            if mean_tg[i] > mean_tg[i - 1] and mean_tg[i] > mean_tg[i + 1]:
                b = float(tempi[i])
                if 40.0 <= b <= 260.0:
                    raw_candidates.append(round(b, 1))
                    if b > 110.0:
                        raw_candidates.append(round(b / 2.0, 1))
                    if b < 85.0:
                        raw_candidates.append(round(b * 2.0, 1))
                    if b > 140.0:
                        raw_candidates.append(round(b / 3.0, 1))
                    if b < 70.0:
                        raw_candidates.append(round(b * 3.0, 1))

        primary_bpm = raw_candidates[0] if raw_candidates else 120.0

        # Cluster and deduplicate candidates within 3.0 BPM
        unique_cands: List[float] = []
        for c in raw_candidates:
            if 42.0 <= c <= 250.0 and not any(abs(c - u) < 3.0 for u in unique_cands):
                unique_cands.append(c)

        if not unique_cands:
            unique_cands = [120.0]

        # Score each candidate hypothesis
        scored_hypotheses: List[Dict[str, Any]] = []
        best_beat_frames = None
        best_score = -1e9
        best_bpm = unique_cands[0]

        for cand in unique_cands:
            tempo_arr, b_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=hop_length,
                start_bpm=cand,
                bpm=cand,
                tightness=100
            )
            tracked_bpm = float(tempo_arr[0] if isinstance(tempo_arr, (list, np.ndarray)) else tempo_arr)
            b_frames = np.clip(b_frames, 0, len(onset_env) - 1)

            if len(b_frames) < 4:
                continue

            beat_times = librosa.frames_to_time(b_frames, sr=sr, hop_length=hop_length)
            avg_onset = float(np.mean(onset_env[b_frames]))
            avg_onset_ratio = min(2.5, avg_onset / mean_onset)
            ibis = np.diff(beat_times)
            std_ibi = float(np.std(ibis)) if len(ibis) > 1 else 0.5
            regularity = 1.0 / (1.0 + std_ibi)

            # Autocorrelation score at beat period
            beat_sec = float(np.median(ibis)) if len(ibis) > 0 else 60.0 / max(30.0, tracked_bpm)
            frame_lag = int(round(beat_sec * (sr / hop_length)))
            ac_score = float(ac_norm[frame_lag]) if frame_lag < len(ac_norm) else 0.0

            # Require fundamental periodicity: penalize if ac_score < 0.15
            ac_penalty = 1.50 if ac_score < 0.15 else 0.0

            # Check 3:2 Hemiola cross-pulse
            ratio_e = beat_sec / tau_e
            is_hemiola = (abs(ratio_e - 1.5) < 0.12)
            hemiola_penalty = 0.50 if is_hemiola else 0.0

            # Harmonic sum (period multiples: 2x and 3x bar/subdivision)
            lag_2 = frame_lag * 2
            lag_3 = frame_lag * 3
            ac_2 = float(ac_norm[lag_2]) if lag_2 < len(ac_norm) else 0.0
            ac_3 = float(ac_norm[lag_3]) if lag_3 < len(ac_norm) else 0.0
            harmonic_support = 0.5 * ac_2 + 0.5 * ac_3

            # Onset density tactus prior: human musical tactus naturally has ~1.4 - 2.4 onsets per beat
            onsets_per_beat = onset_rate * beat_sec
            tactus_density_score = float(np.exp(-0.5 * ((np.log2(onsets_per_beat) - np.log2(1.8)) / 0.5) ** 2))

            # Musical tempo prior: standard range 75 - 155 BPM
            prior = float(np.exp(-0.5 * ((np.log2(tracked_bpm) - np.log2(115.0)) / 0.6) ** 2))

            # Penalty for extreme tactus densities
            density_penalty = 0.0
            if onsets_per_beat > 3.2:
                density_penalty += 0.35
            elif onsets_per_beat < 0.75:
                density_penalty += 0.35

            # Composite hypothesis score
            score = (
                0.20 * avg_onset_ratio +
                0.30 * (ac_score * 3.0) +
                0.15 * regularity +
                0.15 * (harmonic_support * 3.0) +
                0.10 * (tactus_density_score * 3.0) +
                0.10 * (prior * 3.0) -
                density_penalty -
                hemiola_penalty -
                ac_penalty
            )

            # Hypothesis classification
            hyp_type = "primary"
            if is_hemiola:
                hyp_type = "hemiola_or_triplet"
            elif tracked_bpm > 160.0:
                hyp_type = "double_or_eighth"
            elif tracked_bpm < 65.0:
                hyp_type = "half_or_compound"

            hyp_record = {
                "bpm": round(tracked_bpm, 1),
                "score": round(score, 4),
                "confidence": round(min(0.99, max(0.50, ac_score + 0.3)), 2),
                "avg_onset": round(avg_onset, 2),
                "ac_score": round(ac_score, 3),
                "regularity": round(regularity, 3),
                "onsets_per_beat": round(onsets_per_beat, 2),
                "type": hyp_type
            }
            scored_hypotheses.append(hyp_record)

            if score > best_score:
                best_score = score
                best_bpm = round(tracked_bpm, 1)
                best_beat_frames = b_frames

        # Sort hypotheses by score descending
        scored_hypotheses.sort(key=lambda x: x["score"], reverse=True)

        if best_beat_frames is None:
            tempo_arr, best_beat_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=hop_length,
                tightness=100
            )
            best_bpm = float(tempo_arr[0] if isinstance(tempo_arr, (list, np.ndarray)) else tempo_arr)
            best_bpm = round(best_bpm, 1)

        confidence = scored_hypotheses[0]["confidence"] if scored_hypotheses else 0.85
        beat_period = round(60.0 / best_bpm, 4)

        tempo_analysis = TempoAnalysis(
            bpm=best_bpm,
            confidence=confidence,
            is_estimated=(confidence < 0.80),
            primary_bpm=round(primary_bpm, 1),
            selected_bpm=best_bpm,
            beat_period=beat_period,
            alternative_hypotheses=scored_hypotheses[:5]
        )

        return tempo_analysis, best_beat_frames

    def _detect_downbeats(
        self,
        onset_env: np.ndarray,
        beat_frames: np.ndarray,
        beat_times: List[float],
        beats_per_bar: int,
        sr: int
    ) -> List[float]:
        """Identifies downbeats by testing cyclic offsets for maximal onset energy."""
        if len(beat_frames) < beats_per_bar:
            return beat_times[::beats_per_bar] if beat_times else [0.0]

        energies = []
        for offset in range(beats_per_bar):
            indices = np.arange(offset, len(beat_frames), beats_per_bar)
            frames = np.clip(beat_frames[indices], 0, len(onset_env) - 1)
            mean_strength = np.mean(onset_env[frames])
            energies.append(mean_strength)

        best_offset = int(np.argmax(energies))
        downbeat_indices = np.arange(best_offset, len(beat_times), beats_per_bar)
        downbeats = [beat_times[i] for i in downbeat_indices]
        return downbeats
