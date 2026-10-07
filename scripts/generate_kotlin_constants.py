from pathlib import Path
import librosa
import numpy as np
from scipy.signal import butter

ROOT = Path(__file__).resolve().parents[1]
__vqt_filter_fft = librosa.core.cqt.__globals__['__vqt_filter_fft']
freqs = librosa.cqt_frequencies(n_bins=144, fmin=librosa.note_to_hz('C1'), bins_per_octave=24)
alpha = librosa.filters._relative_bandwidth(freqs=freqs)
lengths, _ = librosa.filters.wavelet_lengths(freqs=freqs, sr=22050, window='hann', filter_scale=1, gamma=0, alpha=alpha)

b0, n_fft0, _ = __vqt_filter_fft(11025.0, freqs[-24:], 1, 1, 0.01, window='hann', gamma=0, dtype=np.complex64, alpha=alpha[-24:])
coo = b0.tocoo()

# Butterworth filter SOS for 90Hz and 260Hz
sos_90 = butter(4, 90, 'lowpass', fs=22050, output='sos')
sos_260 = butter(4, 260, 'lowpass', fs=22050, output='sos')

out_path = ROOT / 'mobile' / 'flutter_app' / 'android' / 'app' / 'src' / 'main' / 'kotlin' / 'com' / 'songchordanalyzer' / 'app' / 'CqtConstants.kt'
out_path.parent.mkdir(parents=True, exist_ok=True)

with open(out_path, 'w', encoding='utf-8') as f:
    f.write('package com.songchordanalyzer.app\n\n')
    f.write('object CqtConstants {\n')
    f.write('    const val SAMPLE_RATE: Int = 22050\n')
    f.write('    const val HOP_LENGTH: Int = 2048\n')
    f.write('    const val N_BINS: Int = 144\n')
    f.write('    const val BINS_PER_OCTAVE: Int = 24\n')
    f.write('    const val N_OCTAVES: Int = 6\n')
    f.write('    const val N_FFT: Int = 512\n')
    f.write('    const val TIMESTEP: Int = 108\n')
    f.write('    const val MEAN: Float = -2.2279878897355596f\n')
    f.write('    const val STD: Float = 1.7191329394436938f\n\n')

    f.write(f'    const val NNZ: Int = {len(coo.data)}\n')
    f.write('    val ROW_INDICES = intArrayOf(' + ', '.join(map(str, coo.row)) + ')\n\n')
    f.write('    val COL_INDICES = intArrayOf(' + ', '.join(map(str, coo.col)) + ')\n\n')
    f.write('    val REAL_WEIGHTS = floatArrayOf(' + ', '.join(f'{x:.8e}f' for x in coo.data.real) + ')\n\n')
    f.write('    val IMAG_WEIGHTS = floatArrayOf(' + ', '.join(f'{x:.8e}f' for x in coo.data.imag) + ')\n\n')
    f.write('    val LENGTHS = floatArrayOf(' + ', '.join(f'{x:.8e}f' for x in lengths) + ')\n\n')

    # Butterworth SOS: shape (n_sections, 6)
    f.write('    val SOS_90HZ = arrayOf(\n')
    for sec in sos_90:
        f.write('        floatArrayOf(' + ', '.join(f'{x:.8e}f' for x in sec) + '),\n')
    f.write('    )\n\n')

    f.write('    val SOS_260HZ = arrayOf(\n')
    for sec in sos_260:
        f.write('        floatArrayOf(' + ', '.join(f'{x:.8e}f' for x in sec) + '),\n')
    f.write('    )\n\n')

    f.write('    val KRUMHANSL_MAJOR = floatArrayOf(6.35f, 2.23f, 3.48f, 2.33f, 4.38f, 4.09f, 2.52f, 5.19f, 2.39f, 3.66f, 2.29f, 2.88f)\n')
    f.write('    val KRUMHANSL_MINOR = floatArrayOf(6.33f, 2.68f, 3.52f, 5.38f, 2.60f, 3.53f, 2.54f, 4.75f, 3.98f, 2.69f, 3.34f, 3.17f)\n\n')

    f.write('    val ROOT_NAMES = arrayOf("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")\n')
    f.write('    val BTC_QUALITIES = arrayOf("min", "maj", "dim", "aug", "min6", "maj6", "min7", "minmaj7", "maj7", "7", "dim7", "hdim7", "sus2", "sus4")\n')
    f.write('}\n')

print(f'Successfully generated CqtConstants.kt at {out_path} ({out_path.stat().st_size} bytes)')
