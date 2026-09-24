import 'dart:io';
import 'analysis_engine.dart';
import '../models/song_analysis.dart';
import '../models/analysis_status.dart';
import 'transpose_service.dart';

/// Stage B: Local On-Device Analysis Engine.
/// Designed for offline mobile inference using ONNX Runtime Mobile / ExecuTorch.
class MobileAnalysisEngine implements AnalysisEngine {
  bool isModelLoaded = false;

  Future<void> initializeModels() async {
    // In Stage B, load onnxruntime / executorch models from app storage
    isModelLoaded = true;
  }

  @override
  Future<String> startAnalysis({
    required File audioFile,
    required String songTitle,
  }) async {
    throw UnimplementedError(
      'On-device mobile ML pipeline is undergoing ONNX/ExecuTorch model quantization. '
      'Please use Development Server Mode in Settings for Stage A.',
    );
  }

  @override
  Future<AnalysisStatus> getStatus(String analysisId) async {
    throw UnimplementedError();
  }

  @override
  Future<SongAnalysis> getResult(String analysisId) async {
    throw UnimplementedError();
  }

  @override
  Future<SongAnalysis> transpose({
    required SongAnalysis currentAnalysis,
    required int semitones,
  }) async {
    // Offline local client transposition (works 100% locally with zero network!)
    return TransposeService.transposeSong(currentAnalysis, semitones);
  }

  @override
  Future<SongAnalysis> editChord({
    required SongAnalysis currentAnalysis,
    required int chordIndex,
    required String root,
    required String quality,
    String? bass,
    String? display,
  }) async {
    // Offline local chord editing
    final chords = currentAnalysis.chords;
    if (chordIndex < 0 || chordIndex >= chords.length) {
      throw RangeError('Chord index $chordIndex out of bounds');
    }

    final targetChord = chords[chordIndex];
    final newDisplay = display ?? (bass != null && bass != root ? '$root$quality/$bass' : '$root$quality');

    targetChord.root = root;
    targetChord.quality = quality;
    targetChord.bass = bass ?? root;
    targetChord.display = newDisplay;

    // Update in bar views
    for (final sec in currentAnalysis.sections) {
      for (final bar in sec.bars) {
        for (final c in bar.chords) {
          if ((c.startTime - targetChord.startTime).abs() < 0.05) {
            c.root = root;
            c.quality = quality;
            c.bass = bass ?? root;
            c.display = newDisplay;
          }
        }
        bar.display = bar.chords.map((c) => c.display).join(' | ');
      }
    }

    return currentAnalysis;
  }

  @override
  Future<SongAnalysis> renameSection({
    required SongAnalysis currentAnalysis,
    required String sectionId,
    required String newName,
  }) async {
    for (final sec in currentAnalysis.sections) {
      if (sec.sectionId == sectionId) {
        sec.name = newName.trim().toUpperCase();
        break;
      }
    }
    return currentAnalysis;
  }
}
