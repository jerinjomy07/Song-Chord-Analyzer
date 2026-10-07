package com.songchordanalyzer.app

import kotlin.math.*

data class RawChordEvent(
    val root: String,
    val quality: String,
    val bass: String,
    val inversion: Int,
    val display: String,
    val startTime: Double,
    val endTime: Double,
    val duration: Double,
    val beat: Int,
    var beatDuration: Double,
    var barPosition: Int = 1,
    val confidence: Double,
    val alternatives: List<Map<String, Any>> = emptyList()
)

data class BarEvent(
    val barNumber: Int,
    val startTime: Double,
    val endTime: Double,
    val beats: Int,
    val timeSignature: String,
    val display: String,
    val chords: List<RawChordEvent>
)

data class SectionEvent(
    val sectionId: String,
    val name: String,
    val startTime: Double,
    val endTime: Double,
    val startBar: Int,
    val endBar: Int,
    val bars: List<BarEvent>
)

object ChordPostProcessor {

    /**
     * Decodes a 170-element posterior probability vector with Simplicity Regularization.
     */
    fun decodeSimplicity(
        pVec: FloatArray,
        isFlat: Boolean
    ): Triple<String, String, Double> {
        var topIdx = 0
        var topProb = -1.0f
        for (i in 0 until 170) {
            if (pVec[i] > topProb) {
                topProb = pVec[i]
                topIdx = i
            }
        }

        if (topIdx == 169 || topIdx == 168) {
            return Triple("N", "none", topProb.toDouble())
        }

        val rawRootIdx = topIdx / 14
        val rawQualIdx = topIdx % 14
        val rawRoot = CqtConstants.ROOT_NAMES[rawRootIdx]
        val rawQual = CqtConstants.BTC_QUALITIES[rawQualIdx]

        var finalQual = rawQual
        var finalProb = topProb

        // Simplicity Regularization (User Requirement 4 & 5):
        // In popular/film/folk music, heavily favor base triads.
        if (rawQual in listOf("7", "maj7", "min7", "maj6", "min6", "dim7", "hdim7")) {
            val baseQual = if (rawQual in listOf("min7", "min6", "hdim7")) "min" else if (rawQual == "dim7") "dim" else "maj"
            val baseQualIdx = CqtConstants.BTC_QUALITIES.indexOf(baseQual)
            val baseIdx = rawRootIdx * 14 + baseQualIdx
            val baseProb = if (baseIdx in 0 until 170) pVec[baseIdx] else 0.0f

            val keepExtension = if (rawQual in listOf("maj7", "maj6", "min6", "dim7", "hdim7")) {
                (topProb >= 0.85f) && (topProb > baseProb * 1.8f) && (topProb - baseProb >= 0.25f)
            } else {
                (topProb >= 0.65f) && (topProb > baseProb * 1.4f) && (topProb - baseProb >= 0.15f)
            }

            if (!keepExtension) {
                finalQual = baseQual
                finalProb = min(0.99f, topProb + baseProb)
            }
        }

        val rootDisp = if (isFlat) KeyDetector.enharmonicSharpToFlat(rawRoot) else rawRoot
        return Triple(rootDisp, finalQual, finalProb.toDouble().coerceIn(0.5, 0.99))
    }

    /**
     * Formats musician-ready chord display string (e.g. "F#m", "Bb", "D/F#").
     */
    fun formatDisplay(root: String, quality: String, bass: String, isFlat: Boolean): String {
        if (root == "N" || root == "X") return "N"

        val dispRoot = if (isFlat) KeyDetector.enharmonicSharpToFlat(root) else root
        val qualDisp = when (quality) {
            "maj" -> ""
            "min" -> "m"
            "dim" -> "dim"
            "aug" -> "aug"
            "min6" -> "m6"
            "maj6" -> "6"
            "min7" -> "m7"
            "minmaj7" -> "m(maj7)"
            "maj7" -> "maj7"
            "7" -> "7"
            "dim7" -> "dim7"
            "hdim7" -> "m7b5"
            "sus2" -> "sus2"
            "sus4" -> "sus4"
            else -> quality
        }

        var disp = "$dispRoot$qualDisp"
        if (bass.isNotEmpty() && bass != root && bass != "N") {
            val dispBass = if (isFlat) KeyDetector.enharmonicSharpToFlat(bass) else bass
            disp = "$disp/$dispBass"
        }
        return disp
    }

    /**
     * Run-length merges consecutive identical chords within a measure (v0.1.7).
     * Eliminates repeating chords in bars and guarantees clean musician lead-sheets.
     */
    fun groupConsecutiveChords(
        barSlice: List<RawChordEvent>,
        barNum: Int,
        bStart: Double,
        bEnd: Double,
        beatsPerBar: Int
    ): List<RawChordEvent> {
        if (barSlice.isEmpty()) {
            return listOf(
                RawChordEvent(
                    root = "N",
                    quality = "none",
                    bass = "N",
                    inversion = 0,
                    display = "N",
                    startTime = round(bStart * 1000.0) / 1000.0,
                    endTime = round(bEnd * 1000.0) / 1000.0,
                    duration = round((bEnd - bStart) * 1000.0) / 1000.0,
                    beat = 1,
                    beatDuration = beatsPerBar.toDouble(),
                    barPosition = barNum,
                    confidence = 0.90
                )
            )
        }

        // If all chords are identical, collapse into a single sustained chord for the whole bar
        val uniqueDisplays = barSlice.map { it.display }.distinct()
        if (uniqueDisplays.size == 1) {
            val first = barSlice[0]
            return listOf(
                first.copy(
                    startTime = round(bStart * 1000.0) / 1000.0,
                    endTime = round(bEnd * 1000.0) / 1000.0,
                    duration = round((bEnd - bStart) * 1000.0) / 1000.0,
                    barPosition = barNum,
                    beat = 1,
                    beatDuration = beatsPerBar.toDouble()
                )
            )
        }

        val groups = mutableListOf<RawChordEvent>()
        var curr = barSlice[0]
        var stB = 1
        var endB = 1
        val confs = mutableListOf(curr.confidence)

        for (i in 1 until barSlice.size) {
            val c = barSlice[i]
            if (c.display == curr.display) {
                endB = i + 1
                confs.add(c.confidence)
            } else {
                val g = curr.copy(
                    startTime = round(barSlice[stB - 1].startTime * 1000.0) / 1000.0,
                    endTime = round(barSlice[endB - 1].endTime * 1000.0) / 1000.0,
                    duration = round((barSlice[endB - 1].endTime - barSlice[stB - 1].startTime) * 1000.0) / 1000.0,
                    barPosition = barNum,
                    beat = stB,
                    beatDuration = (endB - stB + 1).toDouble(),
                    confidence = round((confs.average()) * 100.0) / 100.0
                )
                groups.add(g)

                curr = c
                stB = i + 1
                endB = i + 1
                confs.clear()
                confs.add(c.confidence)
            }
        }

        // Add final group
        val finalG = curr.copy(
            startTime = round(barSlice[stB - 1].startTime * 1000.0) / 1000.0,
            endTime = round(barSlice[endB - 1].endTime * 1000.0) / 1000.0,
            duration = round((barSlice[endB - 1].endTime - barSlice[stB - 1].startTime) * 1000.0) / 1000.0,
            barPosition = barNum,
            beat = stB,
            beatDuration = (endB - stB + 1).toDouble(),
            confidence = round((confs.average()) * 100.0) / 100.0
        )
        groups.add(finalG)

        // Boundary snap
        groups[0] = groups[0].copy(startTime = round(bStart * 1000.0) / 1000.0)
        val lastIdx = groups.size - 1
        groups[lastIdx] = groups[lastIdx].copy(
            endTime = round(bEnd * 1000.0) / 1000.0,
            duration = round((bEnd - groups[lastIdx].startTime) * 1000.0) / 1000.0
        )

        return groups
    }

    /**
     * Builds structured MusicalSection list from list of bars.
     */
    fun structureSections(bars: List<BarEvent>): List<SectionEvent> {
        val sections = mutableListOf<SectionEvent>()
        if (bars.isEmpty()) return sections

        val sectionNames = listOf("INTRO", "VERSE 1", "CHORUS", "VERSE 2", "CHORUS", "OUTRO")
        val sectionLengths = listOf(4, 8, 8, 8, 8, 4)

        var currentBarIdx = 0
        for (s in sectionNames.indices) {
            if (currentBarIdx >= bars.size) break
            val name = sectionNames[s]
            val length = sectionLengths[s]
            val endBarIdx = minOf(currentBarIdx + length, bars.size)
            val secBars = bars.subList(currentBarIdx, endBarIdx)

            if (secBars.isNotEmpty()) {
                sections.add(
                    SectionEvent(
                        sectionId = "sec_$s",
                        name = name,
                        startTime = secBars.first().startTime,
                        endTime = secBars.last().endTime,
                        startBar = secBars.first().barNumber,
                        endBar = secBars.last().barNumber,
                        bars = secBars
                    )
                )
            }
            currentBarIdx = endBarIdx
        }

        // Any remaining bars go to Outro
        if (currentBarIdx < bars.size) {
            val remBars = bars.subList(currentBarIdx, bars.size)
            sections.add(
                SectionEvent(
                    sectionId = "sec_${sections.size}",
                    name = "OUTRO",
                    startTime = remBars.first().startTime,
                    endTime = remBars.last().endTime,
                    startBar = remBars.first().barNumber,
                    endBar = remBars.last().barNumber,
                    bars = remBars
                )
            )
        }

        return sections
    }
}
