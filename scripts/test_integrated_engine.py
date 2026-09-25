import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import soundfile as sf
import librosa
import numpy as np
from scipy.signal import butter, sosfilt
from typing import Dict, Any, List, Tuple

def analyze_track(audio_path: Path):
    y, sr = sf.read(str(audio_path))
    if y.ndim > 1:
        y = np.mean(y, axis=1)
    hop = 512
    duration = len(y) / sr
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
    mean_onset = float(np.mean(onset_env)) + 1e-8
    
    # 1. Continuous onset autocorrelation
    max_lag = int(5.5 * sr / hop)
    ac_onset = librosa.autocorrelate(onset_env, max_size=max_lag)
    ac_norm = ac_onset / (ac_onset[0] + 1e-8)
    times = np.arange(len(ac_norm)) * (hop / sr)
    
    # Fundamental eighth-note pulse tau_e
    peaks = []
    for i in range(2, len(ac_norm) - 2):
        if ac_norm[i] > ac_norm[i-1] and ac_norm[i] > ac_norm[i+1] and ac_norm[i] > 0.08:
            peaks.append((times[i], ac_norm[i]))
    sub_cands = [p for p in peaks if 0.16 <= p[0] <= 0.46]
    sub_cands = sorted(sub_cands, key=lambda x: x[1], reverse=True)
    tau_e = sub_cands[0][0] if sub_cands else 0.35
    
    # 2. Tempogram candidates
    tg = librosa.feature.tempogram(onset_envelope=onset_env, sr=sr, hop_length=hop)
    mean_tg = np.mean(tg, axis=1)
    tempi = librosa.tempo_frequencies(tg.shape[0], sr=sr, hop_length=hop)
    
    raw_candidates = []
    for i in range(1, len(mean_tg) - 1):
        if mean_tg[i] > mean_tg[i-1] and mean_tg[i] > mean_tg[i+1]:
            b = float(tempi[i])
            if 40.0 <= b <= 260.0:
                raw_candidates.append(b)
                if b > 110.0: raw_candidates.append(round(b / 2.0, 1))
                if b < 85.0: raw_candidates.append(round(b * 2.0, 1))
                if b > 140.0: raw_candidates.append(round(b / 3.0, 1))
                if b < 70.0: raw_candidates.append(round(b * 3.0, 1))
                
    # Tacti from fundamental subdivision: quarter note (2*tau_e), dotted quarter (3*tau_e)
    raw_candidates.append(round(60.0 / (2.0 * tau_e), 1))
    raw_candidates.append(round(60.0 / (3.0 * tau_e), 1))
    
    unique_cands = []
    for c in raw_candidates:
        if 42.0 <= c <= 250.0 and not any(abs(c - u) < 3.0 for u in unique_cands):
            unique_cands.append(c)
            
    # Track beats and evaluate candidate grids
    tested_grids = []
    for cand in unique_cands:
        tempo_arr, b_frames = librosa.beat.beat_track(
            onset_envelope=onset_env, sr=sr, hop_length=hop,
            start_bpm=cand, bpm=cand, tightness=100
        )
        b_frames = np.clip(b_frames, 0, len(onset_env) - 1)
        if len(b_frames) < 8:
            continue
            
        b_times = librosa.frames_to_time(b_frames, sr=sr, hop_length=hop)
        beat_sec = float(np.median(np.diff(b_times)))
        tracked_bpm = 60.0 / max(0.2, beat_sec)
        
        frame_lag = int(round(beat_sec * (sr / hop)))
        ac_score = float(ac_norm[frame_lag]) if frame_lag < len(ac_norm) else 0.0
        
        # Discard grids with zero autocorrelation periodicity
        if ac_score < 0.15:
            continue
            
        # Hemiola check: ratio to eighth note is ~1.5
        ratio_e = beat_sec / tau_e
        is_hemiola = (abs(ratio_e - 1.5) < 0.12)
        
        # Binary vs ternary subdivision
        idx_half = int(round((beat_sec / 2.0) * sr / hop))
        idx_third = int(round((beat_sec / 3.0) * sr / hop))
        ac_half = float(ac_norm[idx_half]) if idx_half < len(ac_norm) else 0.0
        ac_third = float(ac_norm[idx_third]) if idx_third < len(ac_norm) else 0.0
        is_ternary = (ac_third > 0.22 and ac_third > ac_half * 1.08)
        
        tested_grids.append({
            'bpm': tracked_bpm,
            'beats': b_times.tolist(),
            'frames': b_frames,
            'beat_sec': beat_sec,
            'ac_score': ac_score,
            'is_hemiola': is_hemiola,
            'is_ternary': is_ternary,
            'ac_half': ac_half,
            'ac_third': ac_third
        })
        
    # Chroma & Bass
    sos = butter(4, 130, 'lowpass', fs=sr, output='sos')
    rms_low = librosa.feature.rms(y=sosfilt(sos, y), hop_length=hop)[0]
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop)
    chroma_diff = np.sqrt(np.sum(np.diff(chroma, axis=1) ** 2, axis=0))
    chroma_diff = np.pad(chroma_diff, (1, 0), mode='edge')
    
    # Joint harmonic & rhythmic repetition for bar length identification
    ac_chroma = librosa.autocorrelate(chroma_diff, max_size=max_lag)
    ac_chroma = ac_chroma / (ac_chroma[0] + 1e-8)
    joint = ac_norm * ac_chroma
    
    bar_peaks = []
    for i in range(2, len(joint) - 2):
        if joint[i] > joint[i-1] and joint[i] > joint[i+1] and times[i] >= 0.8:
            bar_peaks.append((float(times[i]), float(joint[i])))
    bar_peaks = sorted(bar_peaks, key=lambda x: x[1], reverse=True)[:5]
    
    # Metric templates
    meter_templates = {
        '2/4': (2, 2, 4, np.array([1.0, 0.40])),
        '3/4': (3, 3, 4, np.array([1.0, 0.35, 0.45])),
        '4/4': (4, 4, 4, np.array([1.0, 0.30, 0.70, 0.30])),
        '6/8': (2, 6, 8, np.array([1.0, 0.40])), # compound duple
        '7/8': (7, 7, 8, np.array([1.0, 0.20, 0.80, 0.20, 0.80, 0.20, 0.20])),
        '12/8': (4, 12, 8, np.array([1.0, 0.30, 0.70, 0.30])), # compound quadruple
    }
    
    all_evaluations = []
    
    for g in tested_grids:
        b_frames = g['frames']
        beat_sec = g['beat_sec']
        tracked_bpm = g['bpm']
        is_ternary = g['is_ternary']
        is_hemiola = g['is_hemiola']
        
        b_onset = onset_env[b_frames]; b_onset = (b_onset - np.mean(b_onset)) / (np.std(b_onset) + 1e-6)
        b_bass = rms_low[b_frames]; b_bass = (b_bass - np.mean(b_bass)) / (np.std(b_bass) + 1e-6)
        b_chroma = chroma_diff[b_frames]; b_chroma = (b_chroma - np.mean(b_chroma)) / (np.std(b_chroma) + 1e-6)
        salience = 0.40 * b_onset + 0.35 * b_bass + 0.25 * b_chroma
        
        ac_beat = np.correlate(salience, salience, mode='full')
        half = len(ac_beat) // 2
        lags = ac_beat[half:half + 16] / (ac_beat[half] + 1e-8)
        
        # Determine candidate meters for this grid
        grid_meters = []
        if is_ternary:
            # Compound meters
            grid_meters.append('6/8')
            grid_meters.append('12/8')
        else:
            # Simple meters
            grid_meters.append('2/4')
            grid_meters.append('3/4')
            grid_meters.append('4/4')
            if tracked_bpm > 110.0:
                grid_meters.append('7/8')
                
        for m_name in grid_meters:
            k, num, den, tmpl = meter_templates[m_name]
            if k >= len(lags):
                continue
            periodicity = float(lags[k])
            
            num_bars = len(salience) // k
            if num_bars < 2:
                continue
            folded = np.mean([salience[i*k : (i+1)*k] for i in range(num_bars)], axis=0)
            
            best_phi_score = -1e9
            best_phi = 0
            for phi in range(k):
                rolled = np.roll(folded, -phi)
                corr = float(np.corrcoef(rolled, tmpl)[0, 1]) if np.std(rolled) > 1e-6 else 0.0
                down_e = float(folded[phi])
                down_c = float(np.mean([b_chroma[i*k + phi] for i in range(num_bars)]))
                ps = 0.50 * corr + 0.30 * max(0.0, down_e) + 0.20 * max(0.0, down_c)
                if ps > best_phi_score:
                    best_phi_score = ps
                    best_phi = phi
                    
            # Contrast
            contrast = periodicity
            if k == 3:
                contrast = periodicity - max(float(lags[2]), float(lags[4]))
            elif k == 2:
                contrast = periodicity - float(lags[1])
            elif k == 4:
                contrast = periodicity - float(lags[3])
            elif k == 7:
                contrast = periodicity - float(lags[6])
                
            # Phrase penalty: lag 4 over lag 2 (2 bars of 2/4)
            phrase_pen = 0.0
            if k == 4 and lags[2] > 0.45 and lags[2] > lags[4] * 1.05 and not is_ternary:
                phrase_pen = 0.20
            elif k == 4 and is_ternary and lags[2] > 0.50 and lags[2] > lags[4] * 1.05:
                # 6/8 over 12/8 if 2 beats is stronger than 4 beats
                phrase_pen = 0.15
                
        # Harmonic and rhythmic bar duration from joint peaks
        # The true measure duration is the strongest joint peak
        # Check compatibility between bar_peaks and candidate meter
            # Harmonic and rhythmic bar duration from joint peaks
            # The true measure duration is the strongest joint peak
            # Check compatibility between bar_peaks and candidate meter
            bar_compat = 0.0
            for b_t, j_val in bar_peaks[:3]:
                # How many beats of length beat_sec fit in b_t?
                n_b = b_t / beat_sec
                if abs(n_b - k) < 0.25:
                    bar_compat = max(bar_compat, j_val)
                elif k == 2 and abs(n_b - 4) < 0.25:
                    # 2 bars of 2/4
                    bar_compat = max(bar_compat, j_val * 0.90)
                elif k == 3 and abs(n_b - 6) < 0.25:
                    # 2 bars of 3/4
                    bar_compat = max(bar_compat, j_val * 0.90)

            # If this meter does not match any observed harmonic/rhythmic bar repetition, heavily penalize
            if bar_compat < 0.15:
                continue
                
            prior = float(np.exp(-0.5 * ((np.log2(tracked_bpm) - np.log2(110.0)) / 0.6) ** 2))
            hemiola_pen = 0.60 if is_hemiola else 0.0
            
            score = 0.30 * periodicity + 0.25 * contrast + 0.20 * best_phi_score + 0.15 * bar_compat + 0.10 * prior - phrase_pen - hemiola_pen
            all_evaluations.append({
                'meter': m_name,
                'num': num,
                'den': den,
                'bpm': round(tracked_bpm, 1),
                'score': round(score, 4),
                'periodicity': round(periodicity, 3),
                'contrast': round(contrast, 3),
                'phi': best_phi,
                'beats': g['beats'],
                'k': k
            })
            
    if not all_evaluations:
        return '4/4', 120.0, 0.5, {}
        
    all_evaluations = sorted(all_evaluations, key=lambda x: x['score'], reverse=True)
    best = all_evaluations[0]
    
    # Build candidate scores map for all 6 meters
    m_best_scores = {}
    for m in ['2/4', '3/4', '4/4', '6/8', '7/8', '12/8']:
        m_matches = [e for e in all_evaluations if e['meter'] == m]
        m_best_scores[m] = m_matches[0]['score'] if m_matches else 0.01
        
    # Softmax distribution
    exp_s = {m: np.exp(s * 4.0) for m, s in m_best_scores.items()}
    sum_exp = sum(exp_s.values()) + 1e-8
    cand_dist = {m: round(float(v / sum_exp), 3) for m, v in exp_s.items()}
    
    return best['meter'], best['bpm'], best['score'], cand_dist

if __name__ == "__main__":
    tracks = [
        ('Golden 12_8', 'tests/golden_meter/12_8/audio.wav', '12/8'),
        ('Golden 2_4', 'tests/golden_meter/2_4/audio.wav', '2/4'),
        ('Golden 3_4', 'tests/golden_meter/3_4/audio.wav', '3/4'),
        ('Golden 4_4', 'tests/golden_meter/4_4/audio.wav', '4/4'),
        ('Golden 6_8', 'tests/golden_meter/6_8/audio.wav', '6/8'),
        ('Golden 7_8', 'tests/golden_meter/7_8/audio.wav', '7/8'),
        ('Bekhayali', 'C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/43f5b483/audio.mp3', '3/4'),
        ('Pavzhamalli', 'C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/2dfd6d87/audio.mp3', '2/4'),
        ('Magale', 'C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/30f48f40/audio.mp3', '3/4'),
        ('Nallaru Po', 'C:/Users/jerin/AppData/Local/SongChordAnalyzer/library/4bb5d8cb/audio.mp3', '4/4'),
    ]

    for label, p, expected in tracks:
        if Path(p).exists():
            winner, bpm, score, dist = analyze_track(Path(p))
            res = 'MATCH' if winner == expected else 'FAIL'
            print(f'[{res}] {label}: Expected {expected}, Got {winner} ({bpm} BPM, score={score}), Conf: {dist.get(winner, 0)}')
