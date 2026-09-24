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

  TempoAnalysis({
    required this.bpm,
    required this.confidence,
    this.isEstimated = false,
  });

  factory TempoAnalysis.fromJson(Map<String, dynamic> json) {
    return TempoAnalysis(
      bpm: (json['bpm'] as num?)?.toDouble() ?? 120.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
      isEstimated: json['is_estimated'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'bpm': bpm,
        'confidence': confidence,
        'is_estimated': isEstimated,
      };
}

class MeterAnalysis {
  final int numerator;
  final int denominator;
  final String display;
  final double confidence;
  final bool isEstimated;

  MeterAnalysis({
    this.numerator = 4,
    this.denominator = 4,
    this.display = '4/4',
    this.confidence = 0.95,
    this.isEstimated = false,
  });

  factory MeterAnalysis.fromJson(Map<String, dynamic> json) {
    return MeterAnalysis(
      numerator: (json['numerator'] as num?)?.toInt() ?? 4,
      denominator: (json['denominator'] as num?)?.toInt() ?? 4,
      display: json['display'] as String? ?? '4/4',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.95,
      isEstimated: json['is_estimated'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() => {
        'numerator': numerator,
        'denominator': denominator,
        'display': display,
        'confidence': confidence,
        'is_estimated': isEstimated,
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

class BeatGrid {
  final double bpm;
  final List<double> beats;
  final List<double> downbeats;

  BeatGrid({
    required this.bpm,
    this.beats = const [],
    this.downbeats = const [],
  });

  factory BeatGrid.fromJson(Map<String, dynamic> json) {
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
    );
  }

  Map<String, dynamic> toJson() => {
        'bpm': bpm,
        'beats': beats,
        'downbeats': downbeats,
      };
}

class SongAnalysis {
  String id;
  String title;
  AudioMetadata metadata;
  KeyAnalysis key;
  TempoAnalysis tempo;
  MeterAnalysis meter;
  BeatGrid beatGrid;
  List<MusicalSection> sections;
  List<ChordPrediction> chords;
  int transposeSemitones;
  String? audioUrl;
  String? localAudioPath;

  SongAnalysis({
    required this.id,
    required this.title,
    required this.metadata,
    required this.key,
    required this.tempo,
    required this.meter,
    required this.beatGrid,
    required this.sections,
    required this.chords,
    this.transposeSemitones = 0,
    this.audioUrl,
    this.localAudioPath,
  });

  factory SongAnalysis.fromJson(Map<String, dynamic> json) {
    return SongAnalysis(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? 'Untitled Song',
      metadata: AudioMetadata.fromJson(
          json['metadata'] as Map<String, dynamic>? ?? {}),
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
    );
  }

  Map<String, dynamic> toJson() => {
        'schema_version': '1.0.0',
        'id': id,
        'title': title,
        'metadata': metadata.toJson(),
        'key': key.toJson(),
        'tempo': tempo.toJson(),
        'meter': meter.toJson(),
        'beat_grid': beatGrid.toJson(),
        'sections': sections.map((e) => e.toJson()).toList(),
        'chords': chords.map((e) => e.toJson()).toList(),
        'transpose_semitones': transposeSemitones,
        'audio_url': audioUrl,
        'local_audio_path': localAudioPath,
      };
}
