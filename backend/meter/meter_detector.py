"""
Time signature / meter estimation module.
Analyzes rhythmic, harmonic, and acoustic periodicities across all six supported meters:
2/4, 3/4, 4/4, 6/8, 7/8, and 12/8.
Provides objective multi-meter scoring without arbitrary bias, downbeat phase detection,
and pickup bar (anacrusis) identification based on harmonic-metric periodicity.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional
import numpy as np
import librosa
import soundfile as sf
from scipy.signal import butter, sosfilt

from backend.models.schemas import MeterAnalysis, TempoAnalysis


class MeterDetectionResult(tuple):
    """
    Backwards-compatible tuple result (meter_analysis, downbeats, pickup_beats)
    which also exposes selected_bpm, selected_beats, and delegates attribute
    lookups directly to meter_analysis.
    """
    def __new__(
        cls,
        meter_analysis: MeterAnalysis,
        downbeats: List[float],
        pickup_beats: int,
        selected_bpm: Optional[float] = None,
        selected_beats: Optional[List[float]] = None
    ):
        instance = super().__new__(cls, (meter_analysis, downbeats, pickup_beats))
        instance.meter_analysis = meter_analysis
        instance.downbeats = downbeats
        instance.pickup_beats = pickup_beats
        instance.selected_bpm = selected_bpm
        instance.selected_beats = selected_beats
        return instance

    def __getattr__(self, name: str):
        return getattr(self.meter_analysis, name)


class MeterDetector:
    def __init__(self, sample_rate: int = 22050):
        self.sample_rate = sample_rate

    def detect_meter(
        self,
        audio_path: Optional[Path] = None,
        beat_times: Optional[List[float]] = None,
        bpm: float = 120.0,
        tempo_info: Optional[TempoAnalysis] = None,
        y: Optional[np.ndarray] = None,
        sr: Optional[int] = None
    ) -> MeterDetectionResult:
        """
        Estimates musical meter / time signature and downbeats across all 6 supported signatures:
        2/4, 3/4, 4/4, 6/8, 7/8, 12/8.
        Returns MeterDetectionResult(meter_analysis, downbeat_times, pickup_beats, selected_bpm, selected_beats).
        """
        if y is None or sr is None:
            if audio_path is None:
                raise ValueError("Either audio_path or (y, sr) must be provided")
            y, sr = sf.read(str(audio_path))
            if y.ndim > 1:
                y = np.mean(y, axis=1)

        hop = 512
        duration = len(y) / sr

        if duration < 2.0:
            meter_analysis = MeterAnalysis(
                numerator=4,
                denominator=4,
                display="4/4",
                confidence=0.70,
                is_estimated=True,
                candidate_scores={"2/4": 0.15, "3/4": 0.15, "4/4": 0.40, "6/8": 0.10, "7/8": 0.10, "12/8": 0.10},
                downbeat_confidence=0.60,
                meter_evidence="Fallback to standard 4/4 due to short audio (< 2.0s)."
            )
            return MeterDetectionResult(meter_analysis, beat_times[::4] if beat_times else [0.0], 0, bpm, beat_times or [0.0])

        # 1. Onset strength envelope
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)

        # 2. Continuous onset autocorrelation
        max_lag = int(5.5 * sr / hop)
        ac_onset = librosa.autocorrelate(onset_env, max_size=max_lag)
        ac_norm = ac_onset / (ac_onset[0] + 1e-8)
        times = np.arange(len(ac_norm)) * (hop / sr)

        # 3. Chroma flux autocorrelation (harmonic change rate)
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
        chroma_diff = np.sqrt(np.sum(np.diff(chroma, axis=1) ** 2, axis=0))
        chroma_diff = np.pad(chroma_diff, (1, 0), mode="edge")
        ac_chroma = librosa.autocorrelate(chroma_diff, max_size=max_lag)
        ac_chroma = ac_chroma / (ac_chroma[0] + 1e-8)

        # 4. PRIMARY MEASURE DURATION from joint repetition
        joint = ac_norm * ac_chroma
        bar_peaks = []
        for i in range(2, len(joint) - 2):
            if joint[i] > joint[i - 1] and joint[i] > joint[i + 1] and times[i] >= 0.85:
                bar_peaks.append((float(times[i]), float(joint[i])))
        bar_peaks = sorted(bar_peaks, key=lambda x: x[1], reverse=True)
        primary_bar_t, primary_bar_joint = bar_peaks[0] if bar_peaks else (2.0, 0.5)

        # 5. Fundamental eighth-note pulse tau_e:
        # Must divide primary_bar_t into Ne in {4, 6, 7, 8, 12}
        sub_peaks = []
        for i in range(2, len(ac_norm) - 2):
            if ac_norm[i] > ac_norm[i - 1] and ac_norm[i] > ac_norm[i + 1] and 0.16 <= times[i] <= 0.52:
                sub_peaks.append((times[i], ac_norm[i]))
        sub_peaks = sorted(sub_peaks, key=lambda x: x[1], reverse=True)

        # Select tau_e that gives clean integer subdivision count Ne
        tau_e = None
        for s_t, s_h in sub_peaks:
            for b_cand in [primary_bar_t, primary_bar_t * 2.0]:
                ratio = b_cand / s_t
                if any(abs(ratio - target) <= 0.22 for target in [4, 6, 7, 8, 12]):
                    tau_e = s_t
                    break
            if tau_e is not None:
                break

        if tau_e is None:
            tau_e = sub_peaks[0][0] if sub_peaks else 0.35

        # 6. Candidate tempi
        tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr, hop_length=hop)
        mean_tg = np.mean(tg, axis=1)
        tempi = librosa.tempo_frequencies(tg.shape[0], sr=sr, hop_length=hop)

        raw_cands = [
            round(60.0 / (2.0 * tau_e), 1),
            round(60.0 / (3.0 * tau_e), 1),
            round(60.0 / tau_e, 1)
        ]
        if bpm > 35.0:
            raw_cands.append(bpm)
        if tempo_info and tempo_info.alternative_hypotheses:
            for alt in tempo_info.alternative_hypotheses:
                alt_b = alt.get("bpm", 0.0)
                if alt_b > 35.0:
                    raw_cands.append(alt_b)

        for i in range(1, len(mean_tg) - 1):
            if mean_tg[i] > mean_tg[i - 1] and mean_tg[i] > mean_tg[i + 1] and 40.0 <= tempi[i] <= 200.0:
                raw_cands.append(round(float(tempi[i]), 1))

        unique_cands: List[float] = []
        for c in raw_cands:
            if 42.0 <= c <= 195.0 and not any(abs(c - u) < 3.0 for u in unique_cands):
                unique_cands.append(c)

        if not unique_cands:
            unique_cands = [120.0]

        # 7. Lowpass filter for acoustic bass energy (<130Hz)
        sos = butter(4, 130, "lowpass", fs=sr, output="sos")
        rms_low = librosa.feature.rms(y=sosfilt(sos, y), hop_length=hop)[0]

        # 8. Evaluate candidate grids across meters
        all_evaluations: List[Dict[str, Any]] = []

        for cand_bpm in unique_cands:
            tempo_arr, b_frames = librosa.beat.beat_track(
                onset_envelope=onset_env,
                sr=sr,
                hop_length=hop,
                start_bpm=cand_bpm,
                bpm=cand_bpm,
                tightness=100
            )
            b_frames = np.clip(b_frames, 0, len(onset_env) - 1)
            if len(b_frames) < 8:
                continue

            b_times = librosa.frames_to_time(b_frames, sr=sr, hop_length=hop)
            beat_sec = float(np.median(np.diff(b_times)))
            tracked_bpm = 60.0 / max(0.2, beat_sec)
            if tracked_bpm > 190.0 or tracked_bpm < 42.0:
                continue

            frame_lag = int(round(beat_sec * (sr / hop)))
            ac_score = float(ac_norm[frame_lag]) if frame_lag < len(ac_norm) else 0.0
            if ac_score < 0.15:
                continue

            # Subdivision Divisibility: M = beat_sec / tau_e
            M = beat_sec / tau_e
            M_round = round(M)
            if abs(M - M_round) > 0.18:
                continue

            # Binary vs Ternary Subdivision
            idx_half = int(round((beat_sec / 2.0) * sr / hop))
            idx_third = int(round((beat_sec / 3.0) * sr / hop))
            ac_half = float(ac_norm[idx_half]) if idx_half < len(ac_norm) else 0.0
            ac_third = float(ac_norm[idx_third]) if idx_third < len(ac_norm) else 0.0
            is_ternary = (tracked_bpm <= 100.0 and ac_third > 0.20 and ac_third > ac_half * 1.05)

            # Beat salience
            b_onset = onset_env[b_frames]
            b_onset = (b_onset - np.mean(b_onset)) / (np.std(b_onset) + 1e-6)
            b_bass = rms_low[b_frames]
            b_bass = (b_bass - np.mean(b_bass)) / (np.std(b_bass) + 1e-6)
            b_chroma = chroma_diff[b_frames]
            b_chroma = (b_chroma - np.mean(b_chroma)) / (np.std(b_chroma) + 1e-6)
            salience = 0.40 * b_onset + 0.35 * b_bass + 0.25 * b_chroma

            ac_beat = np.correlate(salience, salience, mode="full")
            half = len(ac_beat) // 2
            lags = ac_beat[half:half + 16] / (ac_beat[half] + 1e-8)

            eval_list = []
            if is_ternary:
                eval_list.append(("6/8", 2, 6, 8, [("standard", np.array([1.0, 0.40]))]))
                eval_list.append(("12/8", 4, 12, 8, [("standard", np.array([1.0, 0.30, 0.70, 0.30]))]))
            else:
                eval_list.append(("2/4", 2, 2, 4, [("standard", np.array([1.0, 0.40]))]))
                eval_list.append(("3/4", 3, 3, 4, [("standard", np.array([1.0, 0.35, 0.45]))]))
                eval_list.append(("4/4", 4, 4, 4, [("standard", np.array([1.0, 0.30, 0.70, 0.30]))]))
                if tracked_bpm > 100.0:
                    eval_list.append(("7/8", 7, 7, 8, [
                        ("2+2+3", np.array([1.0, 0.20, 0.80, 0.20, 0.80, 0.20, 0.20])),
                        ("2+3+2", np.array([1.0, 0.20, 0.80, 0.20, 0.20, 0.80, 0.20])),
                        ("3+2+2", np.array([1.0, 0.20, 0.20, 0.80, 0.20, 0.80, 0.20])),
                    ]))

            for name, k, num, den, templates in eval_list:
                if k >= len(lags):
                    continue
                periodicity = float(lags[k])

                num_bars = len(salience) // k
                if num_bars < 2:
                    continue
                folded = np.mean([salience[i * k : (i + 1) * k] for i in range(num_bars)], axis=0)

                best_phi_score = -1e9
                best_phi = 0
                best_subgroup = None

                for sub_name, tmpl in templates:
                    for phi in range(k):
                        rolled = np.roll(folded, -phi)
                        corr = float(np.corrcoef(rolled, tmpl)[0, 1]) if np.std(rolled) > 1e-6 else 0.0
                        down_e = float(folded[phi])
                        down_c = float(np.mean([b_chroma[i * k + phi] for i in range(num_bars)]))
                        ps = 0.50 * corr + 0.30 * max(0.0, down_e) + 0.20 * max(0.0, down_c)
                        if ps > best_phi_score:
                            best_phi_score = ps
                            best_phi = phi
                            best_subgroup = sub_name if sub_name != "standard" else None

                contrast = periodicity
                if k == 3:
                    contrast = periodicity - max(float(lags[2]), float(lags[4]))
                elif k == 2:
                    contrast = periodicity - float(lags[1])
                elif k == 4:
                    contrast = periodicity - float(lags[3])
                elif k == 7:
                    contrast = periodicity - float(lags[6])

                # Phrase penalty: prefer 2/4 if lag 2 is stronger than lag 4
                phrase_pen = 0.0
                if k == 4 and lags[2] > 0.35 and lags[2] >= lags[4] * 0.98 and not is_ternary:
                    phrase_pen = 0.25
                elif k == 4 and is_ternary and lags[2] > 0.40 and lags[2] > lags[4] * 1.05:
                    phrase_pen = 0.20
                elif k == 6 and lags[3] > 0.25:
                    phrase_pen = 0.25

                # Primary bar duration compatibility bonus
                K_bar = primary_bar_t / beat_sec
                bar_match_bonus = 0.0
                if abs(K_bar - k) < 0.25:
                    bar_match_bonus = primary_bar_joint * 0.35
                elif k == 2 and abs(K_bar - 4) < 0.25:
                    bar_match_bonus = primary_bar_joint * 0.30

                if is_ternary:
                    prior = float(np.exp(-0.5 * ((np.log2(tracked_bpm) - np.log2(60.0)) / 0.6) ** 2))
                else:
                    prior = float(np.exp(-0.5 * ((np.log2(tracked_bpm) - np.log2(110.0)) / 0.6) ** 2))

                score = (
                    0.35 * periodicity +
                    0.25 * contrast +
                    0.20 * best_phi_score +
                    0.10 * prior +
                    bar_match_bonus -
                    phrase_pen
                )

                all_evaluations.append({
                    "meter": name,
                    "num": num,
                    "den": den,
                    "k": k,
                    "bpm": round(tracked_bpm, 1),
                    "score": round(score, 4),
                    "periodicity": round(periodicity, 3),
                    "contrast": round(contrast, 3),
                    "phase_score": round(best_phi_score, 3),
                    "phi": best_phi,
                    "subgrouping": best_subgroup,
                    "beats": b_times.tolist(),
                })

        if not all_evaluations:
            meter_analysis = MeterAnalysis(
                numerator=4,
                denominator=4,
                display="4/4",
                confidence=0.70,
                is_estimated=True,
                candidate_scores={"2/4": 0.15, "3/4": 0.15, "4/4": 0.40, "6/8": 0.10, "7/8": 0.10, "12/8": 0.10},
                downbeat_confidence=0.60,
                meter_evidence="Fallback to 4/4."
            )
            return MeterDetectionResult(meter_analysis, beat_times[::4] if beat_times else [0.0], 0, bpm, beat_times or [0.0])

        all_evaluations = sorted(all_evaluations, key=lambda x: x["score"], reverse=True)
        winner = all_evaluations[0]

        # Candidate scores map across all 6 meters
        m_best_scores: Dict[str, float] = {}
        for m in ["2/4", "3/4", "4/4", "6/8", "7/8", "12/8"]:
            m_matches = [e for e in all_evaluations if e["meter"] == m]
            m_best_scores[m] = m_matches[0]["score"] if m_matches else 0.01

        exp_s = {m: np.exp(s * 4.0) for m, s in m_best_scores.items()}
        sum_exp = sum(exp_s.values()) + 1e-8
        candidate_conf = {m: round(float(v / sum_exp), 3) for m, v in exp_s.items()}

        selected_meter = winner["meter"]
        selected_beats = winner["beats"]
        selected_bpm = winner["bpm"]
        selected_k = winner["k"]
        selected_phi = winner["phi"]
        subgrouping = winner["subgrouping"]

        downbeats = [selected_beats[i] for i in range(selected_phi, len(selected_beats), selected_k)]
        pickup_beats = selected_phi if selected_phi > 0 else 0
        confidence = candidate_conf.get(selected_meter, 0.85)
        downbeat_confidence = round(min(0.99, max(0.55, winner["phase_score"])), 2)

        meter_evidence = (
            f"Selected {selected_meter} at {selected_bpm:.1f} BPM (periodicity: {winner['periodicity']}, "
            f"contrast: {winner['contrast']}, metric accent: {winner['phase_score']}, downbeat phase: {selected_phi}"
        )
        if subgrouping:
            meter_evidence += f", subgrouping: {subgrouping}"
        meter_evidence += f"). Candidate distribution: {candidate_conf}."

        meter_analysis = MeterAnalysis(
            numerator=winner["num"],
            denominator=winner["den"],
            display=selected_meter,
            confidence=round(confidence, 2),
            is_estimated=(confidence < 0.70),
            candidate_scores=candidate_conf,
            downbeat_confidence=downbeat_confidence,
            meter_evidence=meter_evidence,
            subgrouping=subgrouping
        )

        return MeterDetectionResult(
            meter_analysis=meter_analysis,
            downbeats=downbeats,
            pickup_beats=pickup_beats,
            selected_bpm=selected_bpm,
            selected_beats=selected_beats
        )
