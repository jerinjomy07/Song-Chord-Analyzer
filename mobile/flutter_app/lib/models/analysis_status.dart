enum AnalysisStage {
  idle,
  uploading,
  validating,
  preprocessing,
  separating,
  analyzingBeats,
  analyzingKey,
  analyzingChords,
  analyzingInversion,
  aligningBars,
  detectingSections,
  buildingSheet,
  completed,
  failed,
}

class AnalysisStatus {
  final String analysisId;
  final AnalysisStage stage;
  final int progress;
  final String message;
  final String? error;

  AnalysisStatus({
    required this.analysisId,
    required this.stage,
    required this.progress,
    required this.message,
    this.error,
  });

  factory AnalysisStatus.fromJson(Map<String, dynamic> json) {
    final statusStr = json['status'] as String? ?? 'IDLE';
    AnalysisStage stage;
    switch (statusStr.toUpperCase()) {
      case 'PREPROCESSING':
        stage = AnalysisStage.preprocessing;
        break;
      case 'SEPARATING':
        stage = AnalysisStage.separating;
        break;
      case 'ANALYZING_BEATS':
        stage = AnalysisStage.analyzingBeats;
        break;
      case 'ANALYZING_KEY':
        stage = AnalysisStage.analyzingKey;
        break;
      case 'ANALYZING_CHORDS':
        stage = AnalysisStage.analyzingChords;
        break;
      case 'ANALYZING_INVERSION':
        stage = AnalysisStage.analyzingInversion;
        break;
      case 'ALIGNING_BARS':
        stage = AnalysisStage.aligningBars;
        break;
      case 'DETECTING_SECTIONS':
        stage = AnalysisStage.detectingSections;
        break;
      case 'BUILDING_SHEET':
        stage = AnalysisStage.buildingSheet;
        break;
      case 'COMPLETED':
        stage = AnalysisStage.completed;
        break;
      case 'FAILED':
        stage = AnalysisStage.failed;
        break;
      default:
        stage = AnalysisStage.idle;
    }

    return AnalysisStatus(
      analysisId: json['analysis_id'] as String? ?? '',
      stage: stage,
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      message: json['message'] as String? ?? '',
      error: json['error'] as String?,
    );
  }
}
