"""
Generates verified multi-instrument golden audio benchmarks for all 6 supported musical meters:
2/4, 3/4, 4/4, 6/8, 7/8, and 12/8.
Creates audio.wav and ground_truth.json with exact beat, downbeat, and chord annotations.
"""

from pathlib import Path
import json
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_METER_DIR = ROOT / "tests" / "golden_meter"


def synthesize_drum_sounds(sr: int = 22050):
    """Synthesizes kick, snare, and hi-hat sounds."""
    # Kick: 150ms pitch sweep 130Hz -> 45Hz
    t_kick = np.linspace(0, 0.18, int(sr * 0.18))
    freq_sweep = 45.0 + 85.0 * np.exp(-t_kick * 35.0)
    kick = np.sin(2 * np.pi * np.cumsum(freq_sweep) / sr) * np.exp(-t_kick * 18.0)

    # Snare: 200ms noise + 180Hz body
    t_snare = np.linspace(0, 0.20, int(sr * 0.20))
    noise = np.random.uniform(-1, 1, len(t_snare))
    body = np.sin(2 * np.pi * 180.0 * t_snare) * np.exp(-t_snare * 25.0)
    snare = (0.7 * noise + 0.3 * body) * np.exp(-t_snare * 20.0)

    # Hi-hat: 60ms highpass noise
    t_hat = np.linspace(0, 0.06, int(sr * 0.06))
    hat = np.random.uniform(-1, 1, len(t_hat)) * np.exp(-t_hat * 60.0)

    return kick, snare, hat


def note_to_freq(note: str, octave: int = 4) -> float:
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    semitones = notes.index(note) + (octave - 4) * 12
    return 440.0 * (2.0 ** ((semitones - 9) / 12.0))


def synthesize_chord(root: str, quality: str, duration: float, sr: int = 22050) -> np.ndarray:
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    r_idx = notes.index(root)

    if quality == "major":
        intervals = [0, 4, 7]
    elif quality == "minor":
        intervals = [0, 3, 7]
    elif quality == "7":
        intervals = [0, 4, 7, 10]
    else:
        intervals = [0, 4, 7]

    t = np.linspace(0, duration, int(sr * duration))
    chord_wave = np.zeros_like(t)

    for iv in intervals:
        pitch_idx = (r_idx + iv) % 12
        octave = 3 if iv < 5 else 4
        freq = note_to_freq(notes[pitch_idx], octave)
        # Fundamental + gentle 2nd harmonic
        wave = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 2 * freq * t)
        chord_wave += wave

    # Piano/acoustic decay envelope
    envelope = np.exp(-t * 2.5) * (1.0 - np.exp(-t * 100.0))
    # Add bass root note in octave 2
    f_bass = note_to_freq(root, 2)
    bass_wave = (np.sin(2 * np.pi * f_bass * t) + 0.5 * np.sin(2 * np.pi * 2 * f_bass * t)) * np.exp(-t * 1.8)

    return 0.6 * chord_wave * envelope + 0.4 * bass_wave


def add_sound(buffer: np.ndarray, sound: np.ndarray, start_idx: int):
    end_idx = min(len(buffer), start_idx + len(sound))
    dur = end_idx - start_idx
    if dur > 0:
        buffer[start_idx:end_idx] += sound[:dur]


def generate_meter_track(
    meter_name: str,
    numerator: int,
    denominator: int,
    bpm: float,
    num_bars: int = 16,
    subgrouping: str = None,
    sr: int = 22050
):
    target_dir = GOLDEN_METER_DIR / meter_name.replace("/", "_")
    target_dir.mkdir(parents=True, exist_ok=True)

    kick, snare, hat = synthesize_drum_sounds(sr)

    # Determine subdivision and beat timings
    if denominator == 4:
        # Simple meters: beat is quarter note
        beat_dur = 60.0 / bpm
        sub_dur = beat_dur / 2.0  # eighth note
        bar_dur = numerator * beat_dur
    elif denominator == 8:
        if numerator in [6, 12]:
            # Compound meters: dotted-quarter pulse
            dotted_dur = 60.0 / bpm
            sub_dur = dotted_dur / 3.0  # eighth note
            beat_dur = dotted_dur
            bar_dur = (numerator // 3) * dotted_dur
        elif numerator == 7:
            # Complex additive 7/8: eighth note pulse
            eighth_dur = 60.0 / bpm
            sub_dur = eighth_dur
            beat_dur = eighth_dur
            bar_dur = 7 * eighth_dur

    total_duration = num_bars * bar_dur
    total_samples = int(sr * (total_duration + 1.0))
    audio_buffer = np.zeros(total_samples, dtype=np.float32)

    chords_seq = ["C", "A", "F", "G"] if numerator in [4, 2] else ["A", "G", "F", "E"]
    chords_qual = ["major", "minor", "major", "major"] if numerator in [4, 2] else ["minor", "major", "major", "minor"]

    beats: list[float] = []
    downbeats: list[float] = []
    bars: list[dict] = []
    gt_chords: list[dict] = []

    for bar_i in range(num_bars):
        bar_start = bar_i * bar_dur
        bar_end = bar_start + bar_dur
        downbeats.append(round(bar_start, 3))

        c_root = chords_seq[bar_i % len(chords_seq)]
        c_qual = chords_qual[bar_i % len(chords_qual)]
        disp_chord = f"{c_root}m" if c_qual == "minor" else c_root

        # Synthesize bar harmony
        chord_sound = synthesize_chord(c_root, c_qual, bar_dur, sr)
        add_sound(audio_buffer, chord_sound, int(bar_start * sr))

        gt_chords.append({
            "root": c_root,
            "quality": c_qual,
            "display": disp_chord,
            "start_time": round(bar_start, 3),
            "end_time": round(bar_end, 3),
            "bar": bar_i + 1
        })

        if meter_name == "2/4":
            b1 = bar_start
            b2 = bar_start + beat_dur
            beats.extend([round(b1, 3), round(b2, 3)])
            # Kick on 1, Snare on 2, Hats on eighths
            add_sound(audio_buffer, kick * 1.0, int(b1 * sr))
            add_sound(audio_buffer, hat * 0.4, int((b1 + sub_dur) * sr))
            add_sound(audio_buffer, snare * 0.8, int(b2 * sr))
            add_sound(audio_buffer, hat * 0.4, int((b2 + sub_dur) * sr))

        elif meter_name == "3/4":
            b1 = bar_start
            b2 = bar_start + beat_dur
            b3 = bar_start + 2 * beat_dur
            beats.extend([round(b1, 3), round(b2, 3), round(b3, 3)])
            # Waltz: Kick on 1, Snare/hat on 2 and 3
            add_sound(audio_buffer, kick * 1.0, int(b1 * sr))
            add_sound(audio_buffer, hat * 0.4, int((b1 + sub_dur) * sr))
            add_sound(audio_buffer, snare * 0.6, int(b2 * sr))
            add_sound(audio_buffer, hat * 0.4, int((b2 + sub_dur) * sr))
            add_sound(audio_buffer, snare * 0.6, int(b3 * sr))
            add_sound(audio_buffer, hat * 0.4, int((b3 + sub_dur) * sr))

        elif meter_name == "4/4":
            b_list = [bar_start + i * beat_dur for i in range(4)]
            beats.extend([round(b, 3) for b in b_list])
            # Rock/Pop: Kick on 1 and 3, Snare on 2 and 4
            add_sound(audio_buffer, kick * 1.0, int(b_list[0] * sr))
            add_sound(audio_buffer, snare * 0.8, int(b_list[1] * sr))
            add_sound(audio_buffer, kick * 0.8, int(b_list[2] * sr))
            add_sound(audio_buffer, snare * 0.8, int(b_list[3] * sr))
            for b in b_list:
                add_sound(audio_buffer, hat * 0.35, int((b + sub_dur) * sr))

        elif meter_name == "6/8":
            # 6 eighth notes, 2 dotted-quarter pulses
            b1 = bar_start
            b2 = bar_start + 3 * sub_dur
            beats.extend([round(b1, 3), round(b2, 3)])
            # Kick on 1, Snare on 4, Hats on all eighths
            add_sound(audio_buffer, kick * 1.0, int(b1 * sr))
            add_sound(audio_buffer, snare * 0.8, int(b2 * sr))
            for s_i in range(6):
                add_sound(audio_buffer, hat * 0.35, int((bar_start + s_i * sub_dur) * sr))

        elif meter_name == "7/8":
            # 7 eighth notes, 2+2+3 pattern
            e_times = [bar_start + s_i * sub_dur for s_i in range(7)]
            beats.extend([round(e, 3) for e in e_times])
            # Accents on 1, 3, 5 (2+2+3)
            add_sound(audio_buffer, kick * 1.0, int(e_times[0] * sr))
            add_sound(audio_buffer, snare * 0.7, int(e_times[2] * sr))
            add_sound(audio_buffer, snare * 0.8, int(e_times[4] * sr))
            for e_t in e_times:
                add_sound(audio_buffer, hat * 0.35, int(e_t * sr))

        elif meter_name == "12/8":
            # 12 eighth notes, 4 dotted-quarter pulses
            pulses = [bar_start + p_i * 3 * sub_dur for p_i in range(4)]
            beats.extend([round(p, 3) for p in pulses])
            # Slow shuffle: Kick on 1 and 3, Snare on 2 and 4
            add_sound(audio_buffer, kick * 1.0, int(pulses[0] * sr))
            add_sound(audio_buffer, snare * 0.8, int(pulses[1] * sr))
            add_sound(audio_buffer, kick * 0.8, int(pulses[2] * sr))
            add_sound(audio_buffer, snare * 0.8, int(pulses[3] * sr))
            for s_i in range(12):
                add_sound(audio_buffer, hat * 0.30, int((bar_start + s_i * sub_dur) * sr))

        bars.append({
            "bar_number": bar_i + 1,
            "start_time": round(bar_start, 3),
            "end_time": round(bar_end, 3),
            "chord": disp_chord
        })

    # Normalize audio buffer
    max_val = np.max(np.abs(audio_buffer))
    if max_val > 0:
        audio_buffer = (audio_buffer / max_val) * 0.90

    # Write audio file
    wav_path = target_dir / "audio.wav"
    sf.write(str(wav_path), audio_buffer, sr)

    # Write ground_truth.json
    gt_data = {
        "meter": meter_name,
        "numerator": numerator,
        "denominator": denominator,
        "expected_bpm": bpm,
        "subgrouping": subgrouping,
        "total_bars": num_bars,
        "duration_seconds": round(total_duration, 3),
        "downbeats": downbeats,
        "beats": beats,
        "bars": bars,
        "chords": gt_chords
    }
    with open(target_dir / "ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(gt_data, f, indent=2)

    print(f"Generated {meter_name} benchmark at {wav_path} ({total_duration:.1f}s, {bpm} BPM)")


def main():
    print("Generating Golden Meter Dataset (2/4, 3/4, 4/4, 6/8, 7/8, 12/8)...")
    generate_meter_track("2/4", 2, 4, 120.0, num_bars=16)
    generate_meter_track("3/4", 3, 4, 90.0, num_bars=16)
    generate_meter_track("4/4", 4, 4, 120.0, num_bars=16)
    generate_meter_track("6/8", 6, 8, 55.0, num_bars=16)
    generate_meter_track("7/8", 7, 8, 140.0, num_bars=16, subgrouping="2+2+3")
    generate_meter_track("12/8", 12, 8, 50.0, num_bars=16)
    print("Golden Meter Dataset successfully generated!")


if __name__ == "__main__":
    main()
