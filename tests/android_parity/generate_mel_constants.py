import librosa
import numpy as np

def generate():
    fb = librosa.filters.mel(sr=22050, n_fft=2048, n_mels=128, fmax=11025, htk=False, norm='slaney')
    starts = []
    lens = []
    all_weights = []
    for m in range(128):
        row = fb[m]
        nonzero = np.where(row > 0)[0]
        if len(nonzero) > 0:
            s = int(nonzero[0])
            e = int(nonzero[-1]) + 1
            starts.append(s)
            lens.append(e - s)
            all_weights.extend(row[s:e].astype(np.float32).tolist())
        else:
            starts.append(0)
            lens.append(0)

    target_file = 'mobile/flutter_app/android/app/src/main/kotlin/com/songchordanalyzer/app/MelConstants.kt'
    with open(target_file, 'w', encoding='utf-8') as f:
        f.write('package com.songchordanalyzer.app\n\n')
        f.write('/**\n')
        f.write(' * Precomputed 128-band Slaney Mel filterbank for sr=22050, n_fft=2048, fmax=11025.\n')
        f.write(' * Matches librosa.filters.mel(sr=22050, n_fft=2048, n_mels=128, fmax=11025, norm="slaney").\n')
        f.write(' */\n')
        f.write('object MelConstants {\n')
        f.write('    const val N_MELS = 128\n')
        f.write('    const val N_FFT = 2048\n')
        f.write('    const val HOP_LENGTH = 512\n\n')
        
        f.write('    val STARTS = intArrayOf(\n        ' + ', '.join(map(str, starts)) + '\n    )\n\n')
        f.write('    val LENS = intArrayOf(\n        ' + ', '.join(map(str, lens)) + '\n    )\n\n')
        
        f.write('    val WEIGHTS = floatArrayOf(\n')
        for i in range(0, len(all_weights), 10):
            chunk = all_weights[i:i+10]
            formatted = ', '.join(f'{w:.8f}f' for w in chunk)
            comma = ',' if i + 10 < len(all_weights) else ''
            f.write(f'        {formatted}{comma}\n')
        f.write('    )\n')
        f.write('}\n')

    print(f'Wrote {len(starts)} starts, {len(all_weights)} weights to {target_file}')

if __name__ == '__main__':
    generate()
