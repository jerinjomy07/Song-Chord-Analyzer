package com.songchordanalyzer.app

import kotlin.math.sqrt

data class BassAnalysisResult(
    val bassNote: String,
    val inversion: Int,
    val isSlashChord: Boolean
)

object BassAndInversionAnalyzer {

    /**
     * Filters audio using Second-Order Sections (SOS) Biquad IIR filter.
     */
    fun sosFilter(audio: FloatArray, sos: Array<FloatArray>): FloatArray {
        var current = audio.clone()
        for (sec in sos) {
            val b0 = sec[0]
            val b1 = sec[1]
            val b2 = sec[2]
            val a0 = sec[3]
            val a1 = sec[4]
            val a2 = sec[5]

            val out = FloatArray(current.size)
            var x1 = 0.0f
            var x2 = 0.0f
            var y1 = 0.0f
            var y2 = 0.0f

            for (i in current.indices) {
                val x0 = current[i]
                val y0 = (b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0
                out[i] = y0
                x2 = x1
                x1 = x0
                y2 = y1
                y1 = y0
            }
            current = out
        }
        return current
    }

    /**
     * Analyzes physical bass frequencies in a given beat interval [startTime, endTime].
     * Resolves sounding bass note and inversion (1st, 2nd, 3rd) or slash chord.
     */
    fun analyzeBass(
        audioSub90: FloatArray,
        audioSub260: FloatArray,
        startTime: Double,
        endTime: Double,
        chordRoot: String,
        chordQuality: String,
        sampleRate: Int = 22050
    ): BassAnalysisResult {
        if (chordRoot == "N" || chordRoot == "X") {
            return BassAnalysisResult("N", 0, false)
        }

        val startIdx = (startTime * sampleRate).toInt().coerceIn(0, audioSub90.size - 1)
        val endIdx = (endTime * sampleRate).toInt().coerceIn(startIdx + 1, audioSub90.size)
        val len = endIdx - startIdx

        // 1. Physical Bass Activity Gate (sub-90Hz RMS >= 0.012)
        var sumSq90 = 0.0f
        for (i in startIdx until endIdx) {
            val s = audioSub90[i]
            sumSq90 += s * s
        }
        val rms90 = sqrt(sumSq90 / len)

        if (rms90 < 0.012f) {
            // Bass instrument inactive or inaudible; default to chord root
            return BassAnalysisResult(chordRoot, 0, false)
        }

        // 2. Pitch Chroma Tracking in 260Hz band using autocorrelation / filter energy
        val pitchEnergy = FloatArray(12)
        val rootSemi = CqtConstants.ROOT_NAMES.indexOf(chordRoot)
        if (rootSemi >= 0) pitchEnergy[rootSemi] = 0.5f

        // Calculate pitch class energy in sub-260Hz window
        val maxLag = (sampleRate / 40.0).toInt().coerceAtMost(len - 1) // ~40 Hz
        val minLag = (sampleRate / 260.0).toInt() // ~260 Hz

        for (semi in 0 until 12) {
            val noteFreq = 32.703 * Math.pow(2.0, (semi + 12) / 12.0)
            val noteLag = (sampleRate / noteFreq).toInt()
            if (noteLag in minLag until maxLag) {
                var autoSum = 0.0f
                var count = 0
                for (i in startIdx until (endIdx - noteLag)) {
                    autoSum += audioSub260[i] * audioSub260[i + noteLag]
                    count++
                }
                if (count > 0) {
                    pitchEnergy[semi] += maxOf(0.0f, autoSum / count)
                }
            }
        }

        var topBassSemi = rootSemi
        var maxEnergy = -1.0f
        for (s in 0 until 12) {
            if (pitchEnergy[s] > maxEnergy) {
                maxEnergy = pitchEnergy[s]
                topBassSemi = s
            }
        }

        val topBassNote = if (topBassSemi in 0 until 12) CqtConstants.ROOT_NAMES[topBassSemi] else chordRoot

        if (topBassNote == chordRoot) {
            return BassAnalysisResult(chordRoot, 0, false)
        }

        // 3. Inversion Discrimination
        val interval = if (rootSemi >= 0 && topBassSemi >= 0) {
            (topBassSemi - rootSemi + 12) % 12
        } else {
            0
        }

        var inv = 0
        var isSlash = false

        // 1st Inversion: Third in bass (4 semitones for Major, 3 for Minor)
        if ((chordQuality in listOf("maj", "7", "maj7", "sus4") && interval == 4) ||
            (chordQuality in listOf("min", "min7", "dim", "hdim7") && interval == 3)
        ) {
            inv = 1
            isSlash = true
        }
        // 2nd Inversion: Fifth in bass (7 semitones)
        else if (interval == 7) {
            inv = 2
            isSlash = true
        }
        // 3rd Inversion: Seventh in bass (10 semitones for dom7/min7, 11 for maj7)
        else if (interval in listOf(10, 11)) {
            inv = 3
            isSlash = true
        }
        // Common valid passing slash chords (e.g. D/B -> Bm7, G/E -> Em7, C/D -> D9sus)
        else if (interval in listOf(2, 5, 9)) {
            inv = 1
            isSlash = true
        }

        return if (isSlash) {
            BassAnalysisResult(topBassNote, inv, true)
        } else {
            BassAnalysisResult(chordRoot, 0, false)
        }
    }
}
