package com.songchordanalyzer.app

import kotlin.math.*

/**
 * Extracts log-mel spectral flux onset envelope matching librosa.onset.onset_strength(y, sr=22050, hop_length=512).
 * Uses 2048-point STFT, Hann window, 128-band Slaney Mel filterbank, dB log compression (top_db=80),
 * positive first-order differencing, and pad_width=3 frame alignment.
 */
object SpectralFluxOnset {

    fun extractOnsetEnvelope(audio: FloatArray): FloatArray {
        val nFft = MelConstants.N_FFT // 2048
        val hop = MelConstants.HOP_LENGTH // 512
        val pad = nFft / 2 // 1024
        val nMels = MelConstants.N_MELS // 128

        if (audio.size < hop) {
            return FloatArray(0)
        }

        val nFrames = 1 + audio.size / hop
        val paddedSize = audio.size + 2 * pad
        val paddedAudio = FloatArray(paddedSize)

        // Reflect padding matching librosa np.pad(y, pad_width=1024, mode='reflect')
        for (i in 0 until pad) {
            val src = minOf(1 + i, audio.size - 1)
            paddedAudio[pad - 1 - i] = audio[src]
        }
        System.arraycopy(audio, 0, paddedAudio, pad, audio.size)
        for (i in 0 until pad) {
            val src = maxOf(0, audio.size - 2 - i)
            paddedAudio[pad + audio.size + i] = audio[src]
        }

        val window = FastFourierTransform.hannWindow(nFft)
        val realBuf = FloatArray(nFft)
        val imagBuf = FloatArray(nFft)
        val power = FloatArray(nFft / 2 + 1)

        val melSpec = Array(nMels) { FloatArray(nFrames) }
        var maxMelVal = 1e-10f

        val starts = MelConstants.STARTS
        val lens = MelConstants.LENS
        val weights = MelConstants.WEIGHTS

        val weightOffsets = IntArray(nMels)
        var currOffset = 0
        for (m in 0 until nMels) {
            weightOffsets[m] = currOffset
            currOffset += lens[m]
        }

        for (f in 0 until nFrames) {
            val start = f * hop
            for (k in 0 until nFft) {
                realBuf[k] = paddedAudio[start + k] * window[k]
                imagBuf[k] = 0.0f
            }

            FastFourierTransform.fft(realBuf, imagBuf)

            for (k in 0..nFft / 2) {
                val r = realBuf[k]
                val im = imagBuf[k]
                power[k] = r * r + im * im
            }

            for (m in 0 until nMels) {
                val sBin = starts[m]
                val len = lens[m]
                val off = weightOffsets[m]
                var sum = 0.0f
                for (k in 0 until len) {
                    sum += power[sBin + k] * weights[off + k]
                }
                melSpec[m][f] = sum
                if (sum > maxMelVal) {
                    maxMelVal = sum
                }
            }
        }

        // power_to_db: amin = 1e-10, top_db = 80.0, ref = maxMelVal
        val amin = 1e-10f
        val topDb = 80.0f
        val refDb = 10.0f * log10(maxOf(amin, maxMelVal))
        val minDb = -topDb

        for (m in 0 until nMels) {
            val band = melSpec[m]
            for (f in 0 until nFrames) {
                val p = maxOf(amin, band[f])
                val db = 10.0f * log10(p) - refDb
                band[f] = maxOf(minDb, db)
            }
        }

        // First-order positive difference along frames: max(0, diff) averaged across mel bands
        val onsetEnv = FloatArray(nFrames)
        val padWidth = 1 + nFft / (2 * hop) // 3
        val invMels = 1.0f / nMels.toFloat()

        for (f in 1 until nFrames) {
            var diffSum = 0.0f
            for (m in 0 until nMels) {
                val diff = melSpec[m][f] - melSpec[m][f - 1]
                if (diff > 0.0f) {
                    diffSum += diff
                }
            }
            val targetF = f - 1 + padWidth
            if (targetF < nFrames) {
                onsetEnv[targetF] = diffSum * invMels
            }
        }

        return onsetEnv
    }
}
