enum AnalysisStage {
  idle,
  queued,
  downloading,
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
  postProcessing,
  buildingSheet,
  completed,
  failed,
}

class AnalysisStatus {
  final String analysisId;
  final AnalysisStage stage;
  final String currentStage;
  final int progress;
  final String message;
  final String? error;

  AnalysisStatus({
    required this.analysisId,
    required this.stage,
    this.currentStage = '',
    required this.progress,
    required this.message,
    this.error,
  });

  factory AnalysisStatus.fromJson(Map<String, dynamic> json) {
    final statusStr = (json['status'] as String? ?? 'IDLE').toUpperCase();
    final rawStage = (json['current_stage'] as String? ?? '').toUpperCase();
    final stageKey = rawStage.isNotEmpty ? rawStage : statusStr;

    AnalysisStage stage;
    switch (stageKey) {
      case 'QUEUED':
        stage = AnalysisStage.queued;
        break;
      case 'DOWNLOADING':
        stage = AnalysisStage.downloading;
        break;
      case 'UPLOADING':
        stage = AnalysisStage.uploading;
        break;
      case 'VALIDATING':
        stage = AnalysisStage.validating;
        break;
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
      case 'POST_PROCESSING':
        stage = AnalysisStage.postProcessing;
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
        if (statusStr == 'COMPLETED') {
          stage = AnalysisStage.completed;
        } else if (statusStr == 'FAILED') {
          stage = AnalysisStage.failed;
        } else if (statusStr == 'QUEUED') {
          stage = AnalysisStage.queued;
        } else if (statusStr == 'PROCESSING') {
          stage = AnalysisStage.preprocessing;
        } else {
          stage = AnalysisStage.idle;
        }
    }

    return AnalysisStatus(
      analysisId: json['analysis_id'] as String? ?? '',
      stage: stage,
      currentStage: stageKey,
      progress: (json['progress'] as num?)?.toInt() ?? 0,
      message: json['message'] as String? ?? '',
      error: json['error'] as String?,
    );
  }
}
