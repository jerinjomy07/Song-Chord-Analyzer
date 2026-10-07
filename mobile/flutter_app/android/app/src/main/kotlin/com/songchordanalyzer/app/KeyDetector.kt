package com.songchordanalyzer.app

import kotlin.math.sqrt
import kotlin.math.round

data class KeyResult(
    val tonic: String,
    val mode: String,
    val display: String,
    val confidence: Double,
    val isFlat: Boolean
)

object KeyDetector {

    /**
     * Detects musical key (tonic + mode) fusing Krumhansl-Schmuckler profile correlation (60%)
     * and Triad energy concentration (40%), matching the Windows reference KeyDetector.
     */
    fun detectKey(features: Array<FloatArray>): KeyResult {
        // Accumulate energy across all 144 CQT bins into 12 pitch classes.
        // CQT has 24 bins per octave -> 2 bins per semitone.
        // Therefore, pitch class = (bin / 2) % 12.
        val chroma = FloatArray(12)
        for (f in features) {
            for (b in 0 until CqtConstants.N_BINS) {
                // Denormalize features to magnitude
                val logMag = f[b] * CqtConstants.STD + CqtConstants.MEAN
                val mag = kotlin.math.exp(logMag)
                val pitchClass = (b / 2) % 12
                chroma[pitchClass] += mag
            }
        }

        // L2-normalize chroma vector (matching Windows np.linalg.norm)
        var sumSquares = 0.0
        for (v in chroma) sumSquares += (v * v).toDouble()
        val norm = sqrt(sumSquares).toFloat()
        if (norm > 1e-7f) {
            for (i in chroma.indices) chroma[i] /= norm
        }

        data class KeyCandidate(val rootIdx: Int, val mode: String, val score: Double)
        val candidates = mutableListOf<KeyCandidate>()

        for (root in 0 until 12) {
            // Estimator A: Krumhansl profile correlation
            val rotMajor = FloatArray(12) { i -> CqtConstants.KRUMHANSL_MAJOR[(i - root + 12) % 12] }
            val corrMaj = pearsonCorrelation(chroma, rotMajor)
            val scoreAMaj = maxOf(0.0, ((corrMaj + 1.0) / 2.0).toDouble())

            val rotMinor = FloatArray(12) { i -> CqtConstants.KRUMHANSL_MINOR[(i - root + 12) % 12] }
            val corrMin = pearsonCorrelation(chroma, rotMinor)
            val scoreAMin = maxOf(0.0, ((corrMin + 1.0) / 2.0).toDouble())

            // Estimator B: Triad energy concentration (Root, 3rd, 5th)
            val majEnergy = (chroma[root] + chroma[(root + 4) % 12] + chroma[(root + 7) % 12]) / 3.0
            val minEnergy = (chroma[root] + chroma[(root + 3) % 12] + chroma[(root + 7) % 12]) / 3.0

            // Weighted multi-source fusion: 60% Profile, 40% Triad Energy
            val totalMaj = 0.60 * scoreAMaj + 0.40 * majEnergy
            val totalMin = 0.60 * scoreAMin + 0.40 * minEnergy

            candidates.add(KeyCandidate(root, "major", totalMaj))
            candidates.add(KeyCandidate(root, "minor", totalMin))
        }

        candidates.sortByDescending { it.score }
        val top = candidates[0]
        val runnerUp = if (candidates.size > 1) candidates[1].score else 0.0

        val margin = maxOf(0.0, top.score - runnerUp)
        val confidence = (0.65 + margin * 1.5).coerceIn(0.60, 0.99)

        val rawTonic = CqtConstants.ROOT_NAMES[top.rootIdx]
        val isFlat = isFlatKey(rawTonic, top.mode)
        val displayTonic = if (isFlat) enharmonicSharpToFlat(rawTonic) else rawTonic
        val display = "$displayTonic ${top.mode.replaceFirstChar { it.uppercase() }}"

        return KeyResult(
            tonic = displayTonic,
            mode = top.mode,
            display = display,
            confidence = round(confidence * 100.0) / 100.0,
            isFlat = isFlat
        )
    }

    private fun pearsonCorrelation(x: FloatArray, y: FloatArray): Float {
        var meanX = 0f
        var meanY = 0f
        val n = x.size
        for (i in 0 until n) {
            meanX += x[i]
            meanY += y[i]
        }
        meanX /= n
        meanY /= n

        var num = 0f
        var denX = 0f
        var denY = 0f
        for (i in 0 until n) {
            val dx = x[i] - meanX
            val dy = y[i] - meanY
            num += dx * dy
            denX += dx * dx
            denY += dy * dy
        }
        val den = sqrt(denX * denY)
        return if (den > 0f) num / den else 0f
    }

    fun isFlatKey(keyRoot: String, mode: String): Boolean {
        val root = enharmonicFlatToSharp(keyRoot)
        return if (mode.lowercase().contains("min")) {
            // Minor keys with flats: Dm, Gm, Cm, Fm, Bbm, Ebm
            root in arrayOf("D", "G", "C", "F", "A#", "D#")
        } else {
            // Major keys with flats: F, Bb, Eb, Ab, Db, Gb
            root in arrayOf("F", "A#", "D#", "G#", "C#")
        }
    }

    fun enharmonicSharpToFlat(pitch: String): String = when (pitch) {
        "C#" -> "Db"
        "D#" -> "Eb"
        "F#" -> "Gb"
        "G#" -> "Ab"
        "A#" -> "Bb"
        else -> pitch
    }

    fun enharmonicFlatToSharp(pitch: String): String = when (pitch) {
        "Db" -> "C#"
        "Eb" -> "D#"
        "Gb" -> "F#"
        "Ab" -> "G#"
        "Bb" -> "A#"
        "B#" -> "C"
        "Cb" -> "B"
        "E#" -> "F"
        "Fb" -> "E"
        else -> pitch
    }
}
