package com.songchordanalyzer.app

import kotlin.math.ln
import kotlin.math.pow
import kotlin.math.sqrt

object CqtExtractor {

    /**
     * Decimates an audio signal by a factor of 2 using a 15-tap halfband FIR anti-aliasing filter.
     */
    private fun decimate2(input: FloatArray): FloatArray {
        // High-attenuation 15-tap half-band symmetric FIR filter coefficients (cutoff 0.25 nyquist)
        val h = floatArrayOf(
            -0.0034f, 0.0f, 0.0211f, 0.0f, -0.0768f, 0.0f, 0.3091f, 0.5000f,
            0.3091f, 0.0f, -0.0768f, 0.0f, 0.0211f, 0.0f, -0.0034f
        )
        val filterLen = h.size
        val halfFilter = filterLen / 2
        val outLen = input.size / 2
        val output = FloatArray(outLen)

        for (i in 0 until outLen) {
            val srcIdx = i * 2
            var sum = 0.0f
            for (k in 0 until filterLen) {
                val inPos = srcIdx + k - halfFilter
                if (inPos in input.indices) {
                    sum += input[inPos] * h[k]
                }
            }
            output[i] = sum
        }
        return output
    }

    /**
     * Extracts normalized 144-bin CQT features from 22,050 Hz mono PCM audio.
     * Returns 2D FloatArray: shape [num_frames][144]
     */
    fun extractFeatures(audio: FloatArray): Array<FloatArray> {
        val nFft = CqtConstants.N_FFT // 512
        val padLen = nFft / 2 // 256

        // 1. Early downsample from 22050 to 11025
        val yEarly = decimate2(audio)
        val sqrt2 = sqrt(2.0f)
        for (i in yEarly.indices) {
            yEarly[i] *= sqrt2
        }

        var currentY = yEarly
        var currentHop = 1024 // 2048 / 2

        // Store octave responses: octaveResponses[octaveIdx][binInOctave (0..23)][frameIdx]
        val octaveResponses = Array(6) { Array(24) { FloatArray(0) } }

        val realBuf = FloatArray(nFft)
        val imagBuf = FloatArray(nFft)

        for (oct in 0 until 6) {
            val octaveScale = sqrt(2.0f.pow(oct + 1))
            val nFrames = maxOf(1, (currentY.size + 2 * padLen - nFft) / currentHop + 1)

            for (b in 0 until 24) {
                octaveResponses[oct][b] = FloatArray(nFrames)
            }

            // Pre-allocate padded audio
            val paddedY = FloatArray(currentY.size + 2 * padLen)
            System.arraycopy(currentY, 0, paddedY, padLen, currentY.size)

            for (f in 0 until nFrames) {
                val start = f * currentHop
                for (k in 0 until nFft) {
                    realBuf[k] = paddedY[start + k]
                    imagBuf[k] = 0.0f
                }

                // 512-point FFT
                FastFourierTransform.fft(realBuf, imagBuf)

                // Sparse matrix projection: 303 non-zero entries
                // cqt_bin = sum_{k} basis[bin, k] * X[k]
                val binReal = FloatArray(24)
                val binImag = FloatArray(24)

                for (idx in 0 until CqtConstants.NNZ) {
                    val r = CqtConstants.ROW_INDICES[idx]
                    val c = CqtConstants.COL_INDICES[idx]
                    val wR = CqtConstants.REAL_WEIGHTS[idx]
                    val wI = CqtConstants.IMAG_WEIGHTS[idx]

                    val xR = realBuf[c]
                    val xI = imagBuf[c]

                    binReal[r] += (wR * xR - wI * xI)
                    binImag[r] += (wR * xI + wI * xR)
                }

                for (b in 0 until 24) {
                    val mag = sqrt(binReal[b] * binReal[b] + binImag[b] * binImag[b]) * octaveScale
                    octaveResponses[oct][b][f] = mag
                }
            }

            if (oct < 5) {
                currentHop /= 2
                val nextY = decimate2(currentY)
                for (i in nextY.indices) {
                    nextY[i] *= sqrt2
                }
                currentY = nextY
            }
        }

        // Stack octaves from lowest frequency (octave 5) to highest (octave 0)
        // Trims all octaves to minFrames, exactly matching librosa __trim_stack
        var minFrames = octaveResponses[0][0].size
        for (oct in 1 until 6) {
            val s = octaveResponses[oct][0].size
            if (s < minFrames) minFrames = s
        }

        val features = Array(minFrames) { FloatArray(CqtConstants.N_BINS) }

        for (f in 0 until minFrames) {
            for (oct in 5 downTo 0) {
                val binOffset = (5 - oct) * 24
                for (b in 0 until 24) {
                    val globalBin = binOffset + b
                    val mag = octaveResponses[oct][b][f]
                    val normMag = mag / sqrt(CqtConstants.LENGTHS[globalBin])
                    val logMag = ln(normMag + 1e-6f)
                    features[f][globalBin] = (logMag - CqtConstants.MEAN) / CqtConstants.STD
                }
            }
        }

        return features
    }
}
