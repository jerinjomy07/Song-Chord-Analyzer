package com.songchordanalyzer.app

import kotlin.math.*

/**
 * Dynamic programming beat tracker following Ellis (2007) and librosa.beat.beat_track.
 * Features:
 * - Standard-deviation AGC normalization
 * - Gaussian local score convolution window
 * - Dynamic programming forward accumulation with logarithmic tightness penalty
 * - Backtracking from median-thresholded local maximum
 * - Trim leading/trailing weak onsets using 5-point Hanning envelope
 */
object EllisBeatTracker {

    fun trackBeats(
        onsetEnv: FloatArray,
        bpm: Double,
        sampleRate: Int = 22050,
        hopLength: Int = 512,
        tightness: Double = 100.0,
        trim: Boolean = true
    ): List<Double> {
        val n = onsetEnv.size
        if (n < 4 || bpm <= 0.0) return emptyList()

        val frameRate = sampleRate.toDouble() / hopLength.toDouble()
        val framesPerBeat = round(frameRate * 60.0 / bpm)
        if (framesPerBeat < 1.0) return emptyList()

        // 1. Normalize onsets by standard deviation (ddof=1)
        var sum = 0.0
        for (x in onsetEnv) sum += x
        val mean = sum / n

        var varSum = 0.0
        for (x in onsetEnv) {
            val d = x - mean
            varSum += d * d
        }
        val std = sqrt(varSum / maxOf(1, n - 1))
        val normEnv = FloatArray(n) { i -> (onsetEnv[i] / (std + 1e-12)).toFloat() }

        // 2. Local score smoothing with Gaussian window
        val fpbInt = framesPerBeat.toInt()
        val kLen = 2 * fpbInt + 1
        val win = FloatArray(kLen)
        for (k in -fpbInt..fpbInt) {
            val r = k.toDouble() * 32.0 / framesPerBeat
            win[k + fpbInt] = exp(-0.5 * r * r).toFloat()
        }

        val localScore = FloatArray(n)
        for (i in 0 until n) {
            val kMin = maxOf(0, i + kLen / 2 - n + 1)
            val kMax = minOf(i + kLen / 2, kLen - 1)
            var s = 0.0f
            for (k in kMin..kMax) {
                s += win[k] * normEnv[i + kLen / 2 - k]
            }
            localScore[i] = s
        }

        // 3. Dynamic Programming
        val cumScore = DoubleArray(n)
        val backlink = IntArray(n) { -1 }

        var maxLocal = 0.0f
        for (s in localScore) if (s > maxLocal) maxLocal = s
        val scoreThresh = 0.01 * maxLocal.toDouble()

        var firstBeat = true
        cumScore[0] = localScore[0].toDouble()

        val lnFpb = ln(framesPerBeat)
        val halfFpb = round(framesPerBeat / 2.0).toInt()
        val twoFpb = (2.0 * framesPerBeat).toInt()

        for (i in 0 until n) {
            var bestScore = -1e18
            var beatLoc = -1
            val startLoc = i - halfFpb
            val endLoc = i - twoFpb

            for (loc in startLoc downTo endLoc) {
                if (loc < 0) break
                val diff = (i - loc).toDouble()
                val penalty = tightness * (ln(diff) - lnFpb).pow(2)
                val sc = cumScore[loc] - penalty
                if (sc > bestScore) {
                    bestScore = sc
                    beatLoc = loc
                }
            }

            cumScore[i] = localScore[i].toDouble() + (if (beatLoc >= 0) bestScore else 0.0)

            if (firstBeat && localScore[i] < scoreThresh) {
                backlink[i] = -1
            } else {
                backlink[i] = beatLoc
                firstBeat = false
            }
        }

        // 4. Find last beat: local maxima thresholded by 0.5 * median(local maxima)
        val localMaxima = mutableListOf<Double>()
        for (i in 1 until n - 1) {
            if (cumScore[i] > cumScore[i - 1] && cumScore[i] >= cumScore[i + 1]) {
                localMaxima.add(cumScore[i])
            }
        }

        val medianThresh = if (localMaxima.isNotEmpty()) {
            localMaxima.sort()
            0.5 * localMaxima[localMaxima.size / 2]
        } else {
            0.5 * cumScore[n - 1]
        }

        var tail = n - 1
        for (i in n - 1 downTo 0) {
            val isMax = (i > 0 && i < n - 1 && cumScore[i] > cumScore[i - 1] && cumScore[i] >= cumScore[i + 1])
            if (isMax && cumScore[i] >= medianThresh) {
                tail = i
                break
            }
        }

        // 5. Backtrack from tail
        val beatFrames = mutableListOf<Int>()
        var curr = tail
        while (curr >= 0) {
            beatFrames.add(curr)
            curr = backlink[curr]
        }
        beatFrames.reverse()

        if (beatFrames.isEmpty()) return emptyList()

        // 6. Trim leading/trailing beats if requested
        val finalFrames = if (trim) {
            val w = floatArrayOf(0.0f, 0.5f, 1.0f, 0.5f, 0.0f)
            val numBeats = beatFrames.size
            var smoothSumSq = 0.0

            for (bIdx in 0 until numBeats) {
                var s = 0.0f
                for (k in -2..2) {
                    val src = bIdx + k
                    if (src in 0 until numBeats) {
                        s += localScore[beatFrames[src]] * w[k + 2]
                    }
                }
                smoothSumSq += (s * s)
            }

            val threshold = 0.5f * sqrt((smoothSumSq / maxOf(1, numBeats)).toFloat())

            var minFrame = 0
            while (minFrame < n && localScore[minFrame] <= threshold) {
                minFrame++
            }

            var maxFrame = n - 1
            while (maxFrame >= 0 && localScore[maxFrame] <= threshold) {
                maxFrame--
            }

            beatFrames.filter { it in minFrame..maxFrame }
        } else {
            beatFrames
        }

        val frameToTime = hopLength.toDouble() / sampleRate.toDouble()
        return finalFrames.map { round((it.toDouble() * frameToTime) * 10000.0) / 10000.0 }
    }
}
