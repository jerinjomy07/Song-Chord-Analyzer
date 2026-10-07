package com.songchordanalyzer.app

import kotlin.math.*

data class TempoAndMeterResult(
    val bpm: Double,
    val confidence: Double,
    val numerator: Int,
    val denominator: Int,
    val display: String,
    val candidateScores: Map<String, Double>,
    val beats: List<Double>,
    val downbeats: List<Double>
)

object TempoAndMeterDetector {

    private val SOS_130HZ = arrayOf(
        floatArrayOf(1.1218013e-07f, 2.2436027e-07f, 1.1218013e-07f, 1.0f, -1.9325051f, 0.9338318f),
        floatArrayOf(1.0f, 2.0f, 1.0f, 1.0f, -1.9706976f, 0.97205055f)
    )

    /**
     * Estimates tempo, beats, downbeats, and evaluates all 6 supported time signatures:
     * 2/4, 3/4, 4/4, 6/8, 7/8, 12/8.
     * Uses:
     * - Spectral-flux log-mel onset envelope (matching librosa.onset.onset_strength)
     * - Multi-hypothesis tempo evaluation with tactus priors, autocorrelation, and Ellis DP tracking
     * - Real Ellis DP beat tracking
     * - Harmonic and metric downbeat phase selection across all 6 meters
     */
    fun detectTempoAndMeter(audio: FloatArray, sampleRate: Int = 22050): TempoAndMeterResult {
        val hop = MelConstants.HOP_LENGTH // 512
        val framesPerSec = sampleRate.toDouble() / hop.toDouble()
        val duration = audio.size.toDouble() / sampleRate.toDouble()

        if (duration < 2.0 || audio.size < hop * 8) {
            val defaultBpm = 120.0
            val beatSec = 60.0 / defaultBpm
            val beats = mutableListOf<Double>()
            var t = 0.5
            while (t < duration) {
                beats.add(round(t * 1000.0) / 1000.0)
                t += beatSec
            }
            val downbeats = beats.filterIndexed { idx, _ -> idx % 4 == 0 }
            return TempoAndMeterResult(
                bpm = defaultBpm,
                confidence = 0.70,
                numerator = 4,
                denominator = 4,
                display = "4/4",
                candidateScores = mapOf("2/4" to 0.15, "3/4" to 0.15, "4/4" to 0.40, "6/8" to 0.10, "7/8" to 0.10, "12/8" to 0.10),
                beats = beats,
                downbeats = downbeats
            )
        }

        // 1. Stage 4: Spectral-Flux Log-Mel Onset Envelope
        val onsetEnv = SpectralFluxOnset.extractOnsetEnvelope(audio)
        val nFrames = onsetEnv.size

        // 2. Continuous Autocorrelation of Onset Envelope
        val maxLag = minOf(nFrames - 1, (5.5 * framesPerSec).toInt())
        val minLag = (framesPerSec * 60.0 / 250.0).toInt().coerceAtLeast(4)
        val ac = FloatArray(maxLag)

        for (lag in 0 until maxLag) {
            var sum = 0.0f
            val count = nFrames - lag
            for (i in 0 until count) {
                sum += onsetEnv[i] * onsetEnv[i + lag]
            }
            ac[lag] = sum
        }

        val ac0 = ac[0] + 1e-8f
        for (i in ac.indices) ac[i] /= ac0

        // Fundamental subdivision pulse tau_e in [0.16s, 0.46s]
        val subPeaks = mutableListOf<Pair<Double, Float>>()
        for (lag in 2 until maxLag - 2) {
            val t = lag / framesPerSec
            if (t in 0.16..0.46 && ac[lag] > ac[lag - 1] && ac[lag] > ac[lag + 1]) {
                subPeaks.add(Pair(t, ac[lag]))
            }
        }
        subPeaks.sortByDescending { it.second }
        val tauE = subPeaks.firstOrNull()?.first ?: 0.35

        // Onset rate for tactus density estimation
        var peakCount = 0
        var maxOnset = 0.0f
        for (x in onsetEnv) if (x > maxOnset) maxOnset = x
        val peakThresh = 0.10f * maxOnset
        for (i in 1 until nFrames - 1) {
            if (onsetEnv[i] > onsetEnv[i - 1] && onsetEnv[i] > onsetEnv[i + 1] && onsetEnv[i] > peakThresh) {
                peakCount++
            }
        }
        val onsetRate = peakCount.toDouble() / maxOf(1.0, duration)
        val meanOnset = (onsetEnv.average() + 1e-8).toFloat()

        // 3. Stage 5: Candidate Tempi Generation
        val rawCandidates = mutableListOf<Double>(
            round(60.0 / (2.0 * tauE) * 10.0) / 10.0,
            round(60.0 / (3.0 * tauE) * 10.0) / 10.0,
            round(60.0 / tauE * 10.0) / 10.0
        )

        for (lag in minLag until maxLag - 1) {
            if (ac[lag] > ac[lag - 1] && ac[lag] > ac[lag + 1] && ac[lag] > 0.08f) {
                val b = round((framesPerSec * 60.0 / lag) * 10.0) / 10.0
                if (b in 40.0..250.0) {
                    rawCandidates.add(b)
                    if (b > 110.0) rawCandidates.add(round((b / 2.0) * 10.0) / 10.0)
                    if (b < 85.0) rawCandidates.add(round((b * 2.0) * 10.0) / 10.0)
                    if (b > 140.0) rawCandidates.add(round((b / 3.0) * 10.0) / 10.0)
                    if (b < 70.0) rawCandidates.add(round((b * 3.0) * 10.0) / 10.0)
                }
            }
        }

        // Deduplicate candidates within 3.0 BPM
        val uniqueCandidates = mutableListOf<Double>()
        for (c in rawCandidates) {
            if (c in 42.0..245.0 && uniqueCandidates.none { abs(it - c) < 3.0 }) {
                uniqueCandidates.add(c)
            }
        }
        if (uniqueCandidates.isEmpty()) uniqueCandidates.add(120.0)

        // 4. Stage 5 & 6: Score Hypotheses with Ellis DP Beat Tracking
        data class Hypothesis(
            val bpm: Double,
            val score: Double,
            val confidence: Double,
            val beats: List<Double>
        )

        val scoredHypotheses = mutableListOf<Hypothesis>()

        for (cand in uniqueCandidates) {
            val beats = EllisBeatTracker.trackBeats(
                onsetEnv = onsetEnv,
                bpm = cand,
                sampleRate = sampleRate,
                hopLength = hop,
                tightness = 100.0,
                trim = true
            )
            if (beats.size < 4) continue

            // Compute IBIs
            val ibis = DoubleArray(beats.size - 1) { i -> beats[i + 1] - beats[i] }
            val sortedIbis = ibis.sorted()
            val beatSec = sortedIbis[sortedIbis.size / 2]
            val trackedBpm = 60.0 / maxOf(0.2, beatSec)

            // IBI Regularity
            var sumIbi = 0.0
            for (v in ibis) sumIbi += v
            val meanIbi = sumIbi / ibis.size
            var varIbi = 0.0
            for (v in ibis) {
                val d = v - meanIbi
                varIbi += d * d
            }
            val stdIbi = sqrt(varIbi / maxOf(1, ibis.size - 1))
            val regularity = 1.0 / (1.0 + stdIbi)

            // Mean onset at beat frames
            var beatOnsetSum = 0.0
            for (t in beats) {
                val fIdx = (round(t * framesPerSec).toInt()).coerceIn(0, nFrames - 1)
                beatOnsetSum += onsetEnv[fIdx]
            }
            val avgOnset = beatOnsetSum / beats.size
            val avgOnsetRatio = minOf(2.5, avgOnset / meanOnset)

            // Autocorrelation at beat lag
            val frameLag = round(beatSec * framesPerSec).toInt()
            val acScore = if (frameLag in ac.indices) ac[frameLag] else 0.0f
            val acPenalty = if (acScore < 0.15f) 1.50 else 0.0

            // Hemiola check
            val ratioE = beatSec / tauE
            val isHemiola = abs(ratioE - 1.5) < 0.12
            val hemiolaPenalty = if (isHemiola) 0.50 else 0.0

            // Harmonic support
            val lag2 = frameLag * 2
            val lag3 = frameLag * 3
            val ac2 = if (lag2 in ac.indices) ac[lag2] else 0.0f
            val ac3 = if (lag3 in ac.indices) ac[lag3] else 0.0f
            val harmonicSupport = 0.5f * ac2 + 0.5f * ac3

            // Tactus density prior
            val onsetsPerBeat = onsetRate * beatSec
            val tactusDensityScore = exp(-0.5 * ((log2(onsetsPerBeat) - log2(1.8)) / 0.5).pow(2))

            // Musical tempo prior
            val prior = exp(-0.5 * ((log2(cand) - log2(115.0)) / 0.6).pow(2))

            var densityPenalty = 0.0
            if (onsetsPerBeat > 3.2) densityPenalty += 0.35
            if (onsetsPerBeat < 0.75) densityPenalty += 0.35

            val score = (
                0.20 * avgOnsetRatio +
                0.30 * (acScore * 3.0) +
                0.15 * regularity +
                0.15 * (harmonicSupport * 3.0) +
                0.10 * (tactusDensityScore * 3.0) +
                0.10 * (prior * 3.0) -
                densityPenalty -
                hemiolaPenalty -
                acPenalty
            )

            val conf = (acScore.toDouble() + 0.30).coerceIn(0.50, 0.99)
            scoredHypotheses.add(Hypothesis(round(trackedBpm * 10.0) / 10.0, score, conf, beats))
        }

        scoredHypotheses.sortByDescending { it.score }
        val bestHyp = scoredHypotheses.firstOrNull() ?: Hypothesis(
            bpm = 120.0,
            score = 1.0,
            confidence = 0.75,
            beats = EllisBeatTracker.trackBeats(onsetEnv, 120.0, sampleRate, hop)
        )

        val detectedBpm = bestHyp.bpm
        val beats = bestHyp.beats
        val confidence = bestHyp.confidence

        // 5. Stage 7: Multi-Meter Scoring & Downbeat Phase Selection
        // Evaluates 2/4, 3/4, 4/4, 6/8, 7/8, 12/8
        val meterCandidates = listOf(
            Triple(2, 4, "2/4"),
            Triple(3, 4, "3/4"),
            Triple(4, 4, "4/4"),
            Triple(6, 8, "6/8"),
            Triple(7, 8, "7/8"),
            Triple(12, 8, "12/8")
        )

        // Check if ternary feel
        val beatSec = 60.0 / maxOf(30.0, detectedBpm)
        val idxHalf = round((beatSec / 2.0) * framesPerSec).toInt()
        val idxThird = round((beatSec / 3.0) * framesPerSec).toInt()
        val acHalf = if (idxHalf in ac.indices) ac[idxHalf] else 0.0f
        val acThird = if (idxThird in ac.indices) ac[idxThird] else 0.0f
        val isTernary = (detectedBpm <= 100.0 && acThird > 0.20f && acThird > acHalf * 1.05f)

        // Metric accent templates
        val templates = mapOf(
            "2/4" to floatArrayOf(1.0f, 0.40f),
            "3/4" to floatArrayOf(1.0f, 0.35f, 0.45f),
            "4/4" to floatArrayOf(1.0f, 0.30f, 0.70f, 0.30f),
            "6/8" to floatArrayOf(1.0f, 0.40f),
            "7/8" to floatArrayOf(1.0f, 0.20f, 0.80f, 0.20f, 0.80f, 0.20f, 0.20f),
            "12/8" to floatArrayOf(1.0f, 0.30f, 0.70f, 0.30f)
        )

        // Lowpass 130Hz filter for acoustic bass energy
        val lowpassAudio = BassAndInversionAnalyzer.sosFilter(audio, SOS_130HZ)
        val rmsLow = FloatArray(nFrames)
        for (f in 0 until nFrames) {
            val start = f * hop
            var sumSq = 0.0f
            var cnt = 0
            val kEnd = minOf(start + hop, lowpassAudio.size)
            for (k in start until kEnd) {
                val s = lowpassAudio[k]
                sumSq += s * s
                cnt++
            }
            rmsLow[f] = if (cnt > 0) sqrt(sumSq / cnt) else 0.0f
        }

        // Beat salience fusing onset envelope (55%) and acoustic bass energy (45%)
        val bOnset = FloatArray(beats.size)
        val bBass = FloatArray(beats.size)
        for (i in beats.indices) {
            val f = (round(beats[i] * framesPerSec).toInt()).coerceIn(0, nFrames - 1)
            bOnset[i] = onsetEnv[f]
            bBass[i] = rmsLow[f]
        }

        val meanOnsetB = bOnset.average().toFloat()
        var varOnsetB = 0.0
        for (s in bOnset) { val d = s - meanOnsetB; varOnsetB += d * d }
        val stdOnsetB = sqrt(varOnsetB / maxOf(1, bOnset.size - 1)).toFloat() + 1e-6f

        val meanBassB = bBass.average().toFloat()
        var varBassB = 0.0
        for (s in bBass) { val d = s - meanBassB; varBassB += d * d }
        val stdBassB = sqrt(varBassB / maxOf(1, bBass.size - 1)).toFloat() + 1e-6f

        val beatSalience = FloatArray(beats.size)
        for (i in beats.indices) {
            val normOnset = (bOnset[i] - meanOnsetB) / stdOnsetB
            val normBass = (bBass[i] - meanBassB) / stdBassB
            beatSalience[i] = 0.55f * normOnset + 0.45f * normBass
        }

        // Autocorrelation of beat salience for periodicity lags 1..16
        val lags = FloatArray(16)
        for (l in 0 until 16) {
            var sum = 0.0f
            val count = beatSalience.size - l
            for (i in 0 until count) sum += beatSalience[i] * beatSalience[i + l]
            lags[l] = if (count > 0) sum / count else 0.0f
        }
        val lag0 = lags[0] + 1e-8f
        for (l in lags.indices) lags[l] /= lag0

        val meterScores = mutableMapOf<String, Double>()
        var bestMeter = Triple(4, 4, "4/4")
        var bestMeterScore = -1e9
        var bestPhase = 0
        var bestK = 4

        for (m in meterCandidates) {
            val num = m.first
            val den = m.second
            val tag = m.third

            // Number of beats k per measure
            val k = if (den == 8) {
                if (num == 6) 2 else if (num == 12) 4 else 7
            } else {
                num
            }

            if (k >= lags.size) continue
            val periodicity = lags[k].toDouble()

            // Fold salience into k bins
            val numBars = beatSalience.size / k
            if (numBars < 2) continue

            val folded = FloatArray(k)
            for (bar in 0 until numBars) {
                for (p in 0 until k) {
                    folded[p] += beatSalience[bar * k + p]
                }
            }
            for (p in 0 until k) folded[p] /= numBars.toFloat()

            val tmpl = templates[tag] ?: FloatArray(k) { 1.0f }
            var bestPhiScore = -1e9
            var phiForMeter = 0

            for (phi in 0 until k) {
                // Roll folded by -phi
                val rolled = FloatArray(k) { p -> folded[(p + phi) % k] }
                // Pearson correlation with template
                var rMean = 0.0f; var tMean = 0.0f
                for (p in 0 until k) { rMean += rolled[p]; tMean += tmpl[p] }
                rMean /= k; tMean /= k
                var numCorr = 0.0f; var dR = 0.0f; var dT = 0.0f
                for (p in 0 until k) {
                    val dr = rolled[p] - rMean
                    val dt = tmpl[p] - tMean
                    numCorr += dr * dt
                    dR += dr * dr
                    dT += dt * dt
                }
                val corr = if (dR > 1e-8f && dT > 1e-8f) (numCorr / sqrt(dR * dT)).toDouble() else 0.0
                val downE = maxOf(0.0, folded[phi].toDouble())
                val ps = 0.50 * corr + 0.50 * downE
                if (ps > bestPhiScore) {
                    bestPhiScore = ps
                    phiForMeter = phi
                }
            }

            var contrast = periodicity
            if (k == 3) {
                contrast = periodicity - maxOf(lags[2].toDouble(), lags[4].toDouble())
            } else if (k == 2) {
                contrast = periodicity - lags[1].toDouble()
            } else if (k == 4) {
                contrast = periodicity - lags[3].toDouble()
            } else if (k == 7) {
                contrast = periodicity - lags[6].toDouble()
            }

            var phrasePen = 0.0
            if (k == 4 && lags[2] > 0.35f && lags[2] >= lags[4] * 0.98f && !isTernary) {
                phrasePen = 0.25
            } else if (k == 4 && isTernary && lags[2] > 0.40f && lags[2] > lags[4] * 1.05f) {
                phrasePen = 0.20
            }

            val prior = if (isTernary) {
                exp(-0.5 * ((log2(detectedBpm) - log2(60.0)) / 0.6).pow(2))
            } else {
                exp(-0.5 * ((log2(detectedBpm) - log2(110.0)) / 0.6).pow(2))
            }

            val totalScore = 0.35 * periodicity + 0.25 * contrast + 0.20 * bestPhiScore + 0.10 * prior - phrasePen
            meterScores[tag] = totalScore

            if (totalScore > bestMeterScore) {
                bestMeterScore = totalScore
                bestMeter = m
                bestPhase = phiForMeter
                bestK = k
            }
        }

        // Softmax / exp distribution across candidate meters
        val expScores = meterScores.mapValues { exp(it.value * 4.0) }
        val sumExp = expScores.values.sum().coerceAtLeast(1e-8)
        val normalizedScores = expScores.mapValues { round((it.value / sumExp) * 1000.0) / 1000.0 }

        // 6. Generate Downbeats aligned to real beat indices
        val downbeats = mutableListOf<Double>()
        for (idx in bestPhase until beats.size step bestK) {
            downbeats.add(beats[idx])
        }

        return TempoAndMeterResult(
            bpm = detectedBpm,
            confidence = confidence,
            numerator = bestMeter.first,
            denominator = bestMeter.second,
            display = bestMeter.third,
            candidateScores = normalizedScores,
            beats = beats,
            downbeats = downbeats
        )
    }
}
