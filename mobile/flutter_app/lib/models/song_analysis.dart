import 'chord_prediction.dart';
import 'musical_section.dart';

class KeyAnalysis {
  final String tonic;
  final String mode;
  final String display;
  final double confidence;

  KeyAnalysis({
    required this.tonic,
    required this.mode,
    required this.display,
    required this.confidence,
  });

  factory KeyAnalysis.fromJson(Map<String, dynamic> json) {
    return KeyAnalysis(
      tonic: json['tonic'] as String? ?? 'C',
      mode: json['mode'] as String? ?? 'major',
      display: json['display'] as String? ?? 'C Major',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
    );
  }

  Map<String, dynamic> toJson() => {
        'tonic': tonic,
        'mode': mode,
        'display': display,
        'confidence': confidence,
      };
}

class TempoAnalysis {
  final double bpm;
  final double confidence;
  final bool isEstimated;
  final double? primaryBpm;
  final double? selectedBpm;
  final double? beatPeriod;
  final List<dynamic> alternativeHypotheses;

  TempoAnalysis({
    required this.bpm,
    required this.confidence,
    this.isEstimated = false,
    this.primaryBpm,
    this.selectedBpm,
    this.beatPeriod,
    this.alternativeHypotheses = const [],
  });

  factory TempoAnalysis.fromJson(Map<String, dynamic> json) {
    return TempoAnalysis(
      bpm: (json['bpm'] as num?)?.toDouble() ?? 120.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
      isEstimated: json['is_estimated'] as bool? ?? false,
      primaryBpm: (json['primary_bpm'] as num?)?.toDouble(),
      selectedBpm: (json['selected_bpm'] as num?)?.toDouble(),
      beatPeriod: (json['beat_period'] as num?)?.toDouble(),
      alternativeHypotheses: json['alternative_hypotheses'] as List<dynamic>? ?? [],
    );
  }

  Map<String, dynamic> toJson() => {
        'bpm': bpm,
        'confidence': confidence,
        'is_estimated': isEstimated,
        if (primaryBpm != null) 'primary_bpm': primaryBpm,
        if (selectedBpm != null) 'selected_bpm': selectedBpm,
        if (beatPeriod != null) 'beat_period': beatPeriod,
        'alternative_hypotheses': alternativeHypotheses,
      };
}

class MeterAnalysis {
  final int numerator;
  final int denominator;
  final String display;
  final double confidence;
  final bool isEstimated;
  final Map<String, double> candidateScores;
  final double downbeatConfidence;
  final String meterEvidence;
  final String? subgrouping;

  MeterAnalysis({
    this.numerator = 4,
    this.denominator = 4,
    this.display = '4/4',
    this.confidence = 0.95,
    this.isEstimated = false,
    this.candidateScores = const {},
    this.downbeatConfidence = 0.0,
    this.meterEvidence = '',
    this.subgrouping,
  });

  factory MeterAnalysis.fromJson(Map<String, dynamic> json) {
    final rawScores = json['candidate_scores'] as Map<String, dynamic>? ?? {};
    final scores = rawScores.map((k, v) => MapEntry(k, (v as num).toDouble()));

    return MeterAnalysis(
      numerator: (json['numerator'] as num?)?.toInt() ?? 4,
      denominator: (json['denominator'] as num?)?.toInt() ?? 4,
      display: json['display'] as String? ?? '4/4',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.95,
      isEstimated: json['is_estimated'] as bool? ?? false,
      candidateScores: scores,
      downbeatConfidence: (json['downbeat_confidence'] as num?)?.toDouble() ?? 0.0,
      meterEvidence: json['meter_evidence'] as String? ?? '',
      subgrouping: json['subgrouping'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'numerator': numerator,
        'denominator': denominator,
        'display': display,
        'confidence': confidence,
        'is_estimated': isEstimated,
        'candidate_scores': candidateScores,
        'downbeat_confidence': downbeatConfidence,
        'meter_evidence': meterEvidence,
        if (subgrouping != null) 'subgrouping': subgrouping,
      };
}

class AudioMetadata {
  final String filename;
  final double duration;
  final int sampleRate;
  final int channels;
  final String format;
  final int fileSize;
  final String fileHash;

  AudioMetadata({
    required this.filename,
    required this.duration,
    this.sampleRate = 44100,
    this.channels = 2,
    this.format = 'mp3',
    this.fileSize = 0,
    this.fileHash = '',
  });

  factory AudioMetadata.fromJson(Map<String, dynamic> json) {
    return AudioMetadata(
      filename: json['filename'] as String? ?? 'unknown.mp3',
      duration: (json['duration'] as num?)?.toDouble() ?? 0.0,
      sampleRate: (json['sample_rate'] as num?)?.toInt() ?? 44100,
      channels: (json['channels'] as num?)?.toInt() ?? 2,
      format: json['format'] as String? ?? 'mp3',
      fileSize: (json['file_size_bytes'] as num?)?.toInt() ?? 0,
      fileHash: json['file_hash'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'filename': filename,
        'duration': duration,
        'sample_rate': sampleRate,
        'channels': channels,
        'format': format,
        'file_size_bytes': fileSize,
        'file_hash': fileHash,
      };
}

class PipelineMetadata {
  final String appVersion;
  final String modelName;
  final String modelVersion;
  final String separationModel;
  final String deviceUsed;
  final String timestamp;

  PipelineMetadata({
    this.appVersion = '1.0.0',
    this.modelName = 'BTC-Transformer + Demucs v4 + BassStem',
    this.modelVersion = '1.0',
    this.separationModel = 'htdemucs',
    this.deviceUsed = 'cuda',
    this.timestamp = '',
  });

  factory PipelineMetadata.fromJson(Map<String, dynamic> json) {
    return PipelineMetadata(
      appVersion: json['app_version'] as String? ?? '1.0.0',
      modelName: json['model_name'] as String? ?? 'BTC-Transformer + Demucs v4 + BassStem',
      modelVersion: json['model_version'] as String? ?? '1.0',
      separationModel: json['separation_model'] as String? ?? 'htdemucs',
      deviceUsed: json['device_used'] as String? ?? 'cuda',
      timestamp: json['timestamp'] as String? ?? '',
    );
  }

  Map<String, dynamic> toJson() => {
        'app_version': appVersion,
        'model_name': modelName,
        'model_version': modelVersion,
        'separation_model': separationModel,
        'device_used': deviceUsed,
        'timestamp': timestamp,
      };
}

class BeatGrid {
  final double bpm;
  final List<double> beats;
  final List<double> downbeats;
  final int pickupBeats;
  final List<List<double>> barBoundaries;

  BeatGrid({
    required this.bpm,
    this.beats = const [],
    this.downbeats = const [],
    this.pickupBeats = 0,
    this.barBoundaries = const [],
  });

  factory BeatGrid.fromJson(Map<String, dynamic> json) {
    final rawBoundaries = json['bar_boundaries'] as List<dynamic>? ?? [];
    final boundaries = rawBoundaries.map((b) {
      if (b is List) {
        return b.map((e) => (e as num).toDouble()).toList();
      }
      return <double>[];
    }).toList();

    return BeatGrid(
      bpm: (json['bpm'] as num?)?.toDouble() ?? 120.0,
      beats: (json['beats'] as List<dynamic>?)
              ?.map((e) => (e as num).toDouble())
              .toList() ??
          [],
      downbeats: (json['downbeats'] as List<dynamic>?)
              ?.map((e) => (e as num).toDouble())
              .toList() ??
          [],
      pickupBeats: (json['pickup_beats'] as num?)?.toInt() ?? 0,
      barBoundaries: boundaries,
    );
  }

  Map<String, dynamic> toJson() => {
        'bpm': bpm,
        'beats': beats,
        'downbeats': downbeats,
        'pickup_beats': pickupBeats,
        'bar_boundaries': barBoundaries,
      };
}

class SongAnalysis {
  String schemaVersion;
  String id;
  String title;
  AudioMetadata metadata;
  PipelineMetadata pipelineMetadata;
  KeyAnalysis key;
  TempoAnalysis tempo;
  MeterAnalysis meter;
  BeatGrid beatGrid;
  List<MusicalSection> sections;
  List<ChordPrediction> chords;
  int transposeSemitones;
  String? audioUrl;
  String? localAudioPath;
  bool hasStems;
  Map<String, dynamic>? sourceMetadata;
  List<dynamic>? rawPredictions;
  List<dynamic>? debugView;

  SongAnalysis({
    this.schemaVersion = '1.0.0',
    required this.id,
    required this.title,
    required this.metadata,
    required this.pipelineMetadata,
    required this.key,
    required this.tempo,
    required this.meter,
    required this.beatGrid,
    required this.sections,
    required this.chords,
    this.transposeSemitones = 0,
    this.audioUrl,
    this.localAudioPath,
    this.hasStems = false,
    this.sourceMetadata,
    this.rawPredictions,
    this.debugView,
  });

  factory SongAnalysis.fromJson(Map<String, dynamic> json) {
    return SongAnalysis(
      schemaVersion: json['schema_version'] as String? ?? '1.0.0',
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Untitled Song',
      metadata: AudioMetadata.fromJson(
          json['metadata'] as Map<String, dynamic>? ?? {}),
      pipelineMetadata: PipelineMetadata.fromJson(
          json['pipeline_metadata'] as Map<String, dynamic>? ?? {}),
      key: KeyAnalysis.fromJson(json['key'] as Map<String, dynamic>? ?? {}),
      tempo:
          TempoAnalysis.fromJson(json['tempo'] as Map<String, dynamic>? ?? {}),
      meter:
          MeterAnalysis.fromJson(json['meter'] as Map<String, dynamic>? ?? {}),
      beatGrid:
          BeatGrid.fromJson(json['beat_grid'] as Map<String, dynamic>? ?? {}),
      sections: (json['sections'] as List<dynamic>?)
              ?.map((e) => MusicalSection.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      chords: (json['chords'] as List<dynamic>?)
              ?.map((e) => ChordPrediction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      transposeSemitones:
          (json['transpose_semitones'] as num?)?.toInt() ?? 0,
      audioUrl: json['audio_url'] as String?,
      localAudioPath: json['local_audio_path'] as String?,
      hasStems: json['has_stems'] as bool? ?? false,
      sourceMetadata: json['source_metadata'] as Map<String, dynamic>?,
      rawPredictions: json['raw_predictions'] as List<dynamic>?,
      debugView: json['debug_view'] as List<dynamic>?,
    );
  }

  Map<String, dynamic> toJson() => {
        'schema_version': schemaVersion,
        'id': id,
        'title': title,
        'metadata': metadata.toJson(),
        'pipeline_metadata': pipelineMetadata.toJson(),
        'key': key.toJson(),
        'tempo': tempo.toJson(),
        'meter': meter.toJson(),
        'beat_grid': beatGrid.toJson(),
        'sections': sections.map((e) => e.toJson()).toList(),
        'chords': chords.map((e) => e.toJson()).toList(),
        'transpose_semitones': transposeSemitones,
        if (audioUrl != null) 'audio_url': audioUrl,
        if (localAudioPath != null) 'local_audio_path': localAudioPath,
        'has_stems': hasStems,
        if (sourceMetadata != null) 'source_metadata': sourceMetadata,
        if (rawPredictions != null) 'raw_predictions': rawPredictions,
        if (debugView != null) 'debug_view': debugView,
      };
}
