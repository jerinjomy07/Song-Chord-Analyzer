import 'dart:io';
import '../models/song_analysis.dart';
import '../models/analysis_status.dart';

abstract class AnalysisEngine {
  /// Initiates an analysis job for a local audio file
  Future<String> startAnalysis({
    required File audioFile,
    required String songTitle,
  });

  /// Polls status of a running analysis job
  Future<AnalysisStatus> getStatus(String analysisId);

  /// Retrieves the final SongAnalysis object
  Future<SongAnalysis> getResult(String analysisId);

  /// Transposes the song by the specified semitone offset
  Future<SongAnalysis> transpose({
    required SongAnalysis currentAnalysis,
    required int semitones,
  });

  /// Applies a chord edit
  Future<SongAnalysis> editChord({
    required SongAnalysis currentAnalysis,
    required int chordIndex,
    required String root,
    required String quality,
    String? bass,
    String? display,
  });

  /// Renames a section
  Future<SongAnalysis> renameSection({
    required SongAnalysis currentAnalysis,
    required String sectionId,
    required String newName,
  });
}
