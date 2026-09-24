package com.songchordanalyzer.app

import android.app.ActivityManager
import android.content.Context
import android.os.Build
import androidx.annotation.NonNull
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import ai.onnxruntime.*
import java.io.File
import java.nio.FloatBuffer

class MainActivity: FlutterActivity() {
    private val CHANNEL = "com.songchordanalyzer.app/analysis"
    private var ortEnv: OrtEnvironment? = null
    private var ortSession: OrtSession? = null

    override fun configureFlutterEngine(@NonNull flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "getDeviceInfo" -> {
                    try {
                        val actManager = getSystemService(Context.ACTIVITY_SERVICE) as ActivityManager
                        val memInfo = ActivityManager.MemoryInfo()
                        actManager.getMemoryInfo(memInfo)
                        val totalRamMb = (memInfo.totalMem / (1024 * 1024)).toInt()

                        val tier = when {
                            totalRamMb >= 6000 -> "HIGH"
                            totalRamMb >= 3500 -> "MEDIUM"
                            else -> "LOW"
                        }

                        val info = mapOf(
                            "abi" to Build.SUPPORTED_ABIS.firstOrNull(),
                            "cpuCores" to Runtime.getRuntime().availableProcessors(),
                            "totalRamMb" to totalRamMb,
                            "androidVersion" to Build.VERSION.RELEASE,
                            "apiLevel" to Build.VERSION.SDK_INT,
                            "performanceTier" to tier
                        )
                        result.success(info)
                    } catch (e: Exception) {
                        result.error("DEVICE_INFO_ERROR", e.localizedMessage, null)
                    }
                }

                "initOnnxModel" -> {
                    val modelPath = call.argument<String>("modelPath")
                    if (modelPath == null || !File(modelPath).exists()) {
                        result.error("MODEL_NOT_FOUND", "Model file not found at: $modelPath", null)
                        return@setMethodCallHandler
                    }

                    try {
                        ortEnv = OrtEnvironment.getEnvironment()
                        val sessionOptions = OrtSession.SessionOptions()
                        sessionOptions.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
                        sessionOptions.setIntraOpNumThreads(Runtime.getRuntime().availableProcessors().coerceAtMost(4))

                        ortSession = ortEnv?.createSession(modelPath, sessionOptions)
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("ONNX_INIT_ERROR", e.localizedMessage, null)
                    }
                }

                "runBtcInference" -> {
                    val featuresList = call.argument<List<Double>>("features")
                    val batchSize = call.argument<Int>("batchSize") ?: 1
                    val timesteps = call.argument<Int>("timesteps") ?: 108
                    val featureSize = call.argument<Int>("featureSize") ?: 144

                    if (ortSession == null || ortEnv == null) {
                        result.error("MODEL_NOT_READY", "ONNX session not initialized", null)
                        return@setMethodCallHandler
                    }

                    if (featuresList == null || featuresList.size != batchSize * timesteps * featureSize) {
                        result.error("INVALID_INPUT_SHAPE", "Input features size does not match expected shape", null)
                        return@setMethodCallHandler
                    }

                    try {
                        val floatArray = FloatArray(featuresList.size) { i -> featuresList[i].toFloat() }
                        val floatBuffer = FloatBuffer.wrap(floatArray)
                        val shape = longArrayOf(batchSize.toLong(), timesteps.toLong(), featureSize.toLong())

                        val inputTensor = OnnxTensor.createTensor(ortEnv, floatBuffer, shape)
                        val output = ortSession?.run(mapOf("cqt_features" to inputTensor))

                        @Suppress("UNCHECKED_CAST")
                        val logitsTensor = output?.get(0)?.value as Array<Array<FloatArray>>
                        // Flatten to list of doubles: shape (batchSize, timesteps, 170)
                        val flattened = mutableListOf<Double>()
                        for (b in 0 until batchSize) {
                            for (t in 0 until timesteps) {
                                for (c in 0 until 170) {
                                    flattened.add(logitsTensor[b][t][c].toDouble())
                                }
                            }
                        }

                        inputTensor.close()
                        output.close()
                        result.success(flattened)
                    } catch (e: Exception) {
                        result.error("INFERENCE_ERROR", e.localizedMessage, null)
                    }
                }

                "closeOnnxModel" -> {
                    try {
                        ortSession?.close()
                        ortEnv?.close()
                        ortSession = null
                        ortEnv = null
                        result.success(true)
                    } catch (e: Exception) {
                        result.error("CLOSE_ERROR", e.localizedMessage, null)
                    }
                }

                else -> result.notImplemented()
            }
        }
    }
}
