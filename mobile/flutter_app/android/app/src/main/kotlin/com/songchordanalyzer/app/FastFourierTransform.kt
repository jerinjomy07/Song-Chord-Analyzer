package com.songchordanalyzer.app

import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.math.PI

object FastFourierTransform {
    /**
     * In-place Radix-2 Cooley-Tukey FFT.
     * real and imag must have length N where N is a power of 2.
     */
    fun fft(real: FloatArray, imag: FloatArray) {
        val n = real.size
        require(n and (n - 1) == 0) { "FFT size must be a power of 2, got $n" }

        // Bit-reversal permutation
        var j = 0
        for (i in 0 until n - 1) {
            if (i < j) {
                val tempR = real[i]
                real[i] = real[j]
                real[j] = tempR

                val tempI = imag[i]
                imag[i] = imag[j]
                imag[j] = tempI
            }
            var k = n shr 1
            while (k <= j) {
                j -= k
                k = k shr 1
            }
            j += k
        }

        // Cooley-Tukey butterflies
        var len = 2
        while (len <= n) {
            val halfLen = len shr 1
            val angle = (-2.0 * PI / len).toFloat()
            val wStepR = cos(angle.toDouble()).toFloat()
            val wStepI = sin(angle.toDouble()).toFloat()

            var i = 0
            while (i < n) {
                var wR = 1.0f
                var wI = 0.0f
                for (k in 0 until halfLen) {
                    val uR = real[i + k]
                    val uI = imag[i + k]

                    val tR = real[i + k + halfLen] * wR - imag[i + k + halfLen] * wI
                    val tI = real[i + k + halfLen] * wI + imag[i + k + halfLen] * wR

                    real[i + k] = uR + tR
                    imag[i + k] = uI + tI
                    real[i + k + halfLen] = uR - tR
                    imag[i + k + halfLen] = uI - tI

                    val nextWR = wR * wStepR - wI * wStepI
                    val nextWI = wR * wStepI + wI * wStepR
                    wR = nextWR
                    wI = nextWI
                }
                i += len
            }
            len = len shl 1
        }
    }

    /**
     * Computes Hann window coefficients of length N.
     */
    fun hannWindow(n: Int): FloatArray {
        val w = FloatArray(n)
        for (i in 0 until n) {
            w[i] = (0.5 * (1.0 - cos(2.0 * PI * i / n))).toFloat()
        }
        return w
    }
}
