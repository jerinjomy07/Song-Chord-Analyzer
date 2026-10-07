package com.songchordanalyzer.app

import android.media.MediaCodec
import android.media.MediaExtractor
import android.media.MediaFormat
import java.io.File
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.roundToInt

object AudioDecoder {

    var lastPeakBefore: Float = 0.0f
    var lastPeakAfter: Float = 0.0f

    /**
     * Normalizes audio peak amplitude to 0.95 (matching Windows soundfile_load_normalized).
     */
    fun normalizePcm(raw: FloatArray): FloatArray {
        var peak = 0.0f
        for (i in raw.indices) {
            val a = kotlin.math.abs(raw[i])
            if (a > peak) peak = a
        }
        lastPeakBefore = peak
        if (peak > 1e-4f) {
            val scale = 0.95f / peak
            for (i in raw.indices) {
                raw[i] *= scale
            }
            lastPeakAfter = 0.95f
        } else {
            lastPeakAfter = peak
        }
        return raw
    }

    /**
     * Decodes any supported audio format (MP3, WAV, M4A, AAC, FLAC, OGG)
     * into a normalized mono FloatArray sampled at targetSampleRate (22,050 Hz).
     */
    fun decodeAudio(filePath: String, targetSampleRate: Int = 22050): FloatArray {
        val file = File(filePath)
        require(file.exists()) { "Audio file not found: $filePath" }

        // Fast path: If PCM WAV file, parse directly
        val raw = if (filePath.endsWith(".wav", ignoreCase = true)) {
            val wavSamples = try { readWavPcm(file, targetSampleRate) } catch (_: Exception) { null }
            wavSamples?.takeIf { it.isNotEmpty() } ?: decodeWithMediaCodec(filePath, targetSampleRate)
        } else {
            decodeWithMediaCodec(filePath, targetSampleRate)
        }

        return normalizePcm(raw)
    }

    private fun decodeWithMediaCodec(filePath: String, targetSampleRate: Int): FloatArray {
        val extractor = MediaExtractor()
        extractor.setDataSource(filePath)

        var trackIndex = -1
        var format: MediaFormat? = null
        for (i in 0 until extractor.trackCount) {
            val trackFormat = extractor.getTrackFormat(i)
            val mime = trackFormat.getString(MediaFormat.KEY_MIME) ?: ""
            if (mime.startsWith("audio/")) {
                trackIndex = i
                format = trackFormat
                break
            }
        }

        require(trackIndex >= 0 && format != null) { "No audio track found in $filePath" }

        extractor.selectTrack(trackIndex)
        val mime = format.getString(MediaFormat.KEY_MIME)!!
        val origSampleRate = if (format.containsKey(MediaFormat.KEY_SAMPLE_RATE)) {
            format.getInteger(MediaFormat.KEY_SAMPLE_RATE)
        } else {
            44100
        }
        val channelCount = if (format.containsKey(MediaFormat.KEY_CHANNEL_COUNT)) {
            format.getInteger(MediaFormat.KEY_CHANNEL_COUNT)
        } else {
            2
        }

        val codec = MediaCodec.createDecoderByType(mime)
        codec.configure(format, null, null, 0)
        codec.start()

        val pcmList = mutableListOf<Float>()
        val bufferInfo = MediaCodec.BufferInfo()
        var sawInputEOS = false
        var sawOutputEOS = false
        val timeoutUs = 5000L

        while (!sawOutputEOS) {
            if (!sawInputEOS) {
                val inIndex = codec.dequeueInputBuffer(timeoutUs)
                if (inIndex >= 0) {
                    val inputBuffer = codec.getInputBuffer(inIndex)
                    if (inputBuffer != null) {
                        val sampleSize = extractor.readSampleData(inputBuffer, 0)
                        if (sampleSize < 0) {
                            codec.queueInputBuffer(inIndex, 0, 0, 0L, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
                            sawInputEOS = true
                        } else {
                            val presentationTimeUs = extractor.sampleTime
                            codec.queueInputBuffer(inIndex, 0, sampleSize, presentationTimeUs, 0)
                            extractor.advance()
                        }
                    }
                }
            }

            val outIndex = codec.dequeueOutputBuffer(bufferInfo, timeoutUs)
            if (outIndex >= 0) {
                val outputBuffer = codec.getOutputBuffer(outIndex)
                if (outputBuffer != null && bufferInfo.size > 0) {
                    outputBuffer.position(bufferInfo.offset)
                    outputBuffer.limit(bufferInfo.offset + bufferInfo.size)
                    outputBuffer.order(ByteOrder.LITTLE_ENDIAN)

                    val shortBuffer = outputBuffer.asShortBuffer()
                    val numSamples = shortBuffer.remaining()
                    val frameCount = numSamples / channelCount

                    for (f in 0 until frameCount) {
                        var sum = 0f
                        for (ch in 0 until channelCount) {
                            sum += shortBuffer.get() / 32768.0f
                        }
                        pcmList.add(sum / channelCount)
                    }
                }
                codec.releaseOutputBuffer(outIndex, false)
                if ((bufferInfo.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM) != 0) {
                    sawOutputEOS = true
                }
            }
        }

        codec.stop()
        codec.release()
        extractor.release()

        val rawPcm = pcmList.toFloatArray()
        return if (origSampleRate != targetSampleRate) {
            resampleLinear(rawPcm, origSampleRate, targetSampleRate)
        } else {
            rawPcm
        }
    }

    private fun readWavPcm(file: File, targetSampleRate: Int): FloatArray? {
        val fis = FileInputStream(file)
        val header = ByteArray(44)
        if (fis.read(header) < 44) {
            fis.close()
            return null
        }

        val riff = String(header, 0, 4)
        val wave = String(header, 8, 4)
        if (riff != "RIFF" || wave != "WAVE") {
            fis.close()
            return null
        }

        val byteBuffer = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN)
        val channels = byteBuffer.getShort(22).toInt()
        val sampleRate = byteBuffer.getInt(24)
        val bitsPerSample = byteBuffer.getShort(34).toInt()

        val rawBytes = fis.readBytes()
        fis.close()

        val sampleBuffer = ByteBuffer.wrap(rawBytes).order(ByteOrder.LITTLE_ENDIAN)
        val pcmList = FloatArray(rawBytes.size / (channels * (bitsPerSample / 8)))

        when (bitsPerSample) {
            16 -> {
                val shortBuf = sampleBuffer.asShortBuffer()
                var p = 0
                while (shortBuf.hasRemaining() && p < pcmList.size) {
                    var sum = 0f
                    for (ch in 0 until channels) {
                        if (shortBuf.hasRemaining()) sum += shortBuf.get() / 32768.0f
                    }
                    pcmList[p++] = sum / channels
                }
            }
            32 -> {
                val floatBuf = sampleBuffer.asFloatBuffer()
                var p = 0
                while (floatBuf.hasRemaining() && p < pcmList.size) {
                    var sum = 0f
                    for (ch in 0 until channels) {
                        if (floatBuf.hasRemaining()) sum += floatBuf.get()
                    }
                    pcmList[p++] = sum / channels
                }
            }
            else -> return null
        }

        return if (sampleRate != targetSampleRate) {
            resampleLinear(pcmList, sampleRate, targetSampleRate)
        } else {
            pcmList
        }
    }

    /**
     * High-quality linear interpolation resampler.
     */
    fun resampleLinear(input: FloatArray, origSr: Int, targetSr: Int): FloatArray {
        if (origSr == targetSr || input.isEmpty()) return input
        val ratio = origSr.toDouble() / targetSr.toDouble()
        val outputLength = (input.size / ratio).toInt()
        val output = FloatArray(outputLength)

        for (i in 0 until outputLength) {
            val srcPos = i * ratio
            val srcIdx = srcPos.toInt()
            val frac = (srcPos - srcIdx).toFloat()

            if (srcIdx + 1 < input.size) {
                output[i] = input[srcIdx] * (1.0f - frac) + input[srcIdx + 1] * frac
            } else if (srcIdx < input.size) {
                output[i] = input[srcIdx]
            }
        }
        return output
    }
}
