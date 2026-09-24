class ChordCandidate {
  final String chord;
  final double probability;

  ChordCandidate({
    required this.chord,
    required this.probability,
  });

  factory ChordCandidate.fromJson(Map<String, dynamic> json) {
    return ChordCandidate(
      chord: json['chord'] as String? ?? 'N',
      probability: (json['probability'] as num?)?.toDouble() ?? 0.0,
    );
  }

  Map<String, dynamic> toJson() => {
        'chord': chord,
        'probability': probability,
      };
}

class ChordPrediction {
  String root;
  String quality;
  String bass;
  int inversion;
  String display;
  final double startTime;
  final double endTime;
  final double duration;
  int beat;
  double beatDuration;
  final double confidence;
  bool needsReview;
  List<ChordCandidate> alternatives;

  ChordPrediction({
    required this.root,
    required this.quality,
    required this.bass,
    this.inversion = 0,
    required this.display,
    required this.startTime,
    required this.endTime,
    required this.duration,
    this.beat = 1,
    this.beatDuration = 1.0,
    required this.confidence,
    this.needsReview = false,
    this.alternatives = const [],
  });

  factory ChordPrediction.fromJson(Map<String, dynamic> json) {
    return ChordPrediction(
      root: json['root'] as String? ?? 'C',
      quality: json['quality'] as String? ?? 'major',
      bass: json['bass'] as String? ?? (json['root'] as String? ?? 'C'),
      inversion: (json['inversion'] as num?)?.toInt() ?? 0,
      display: json['display'] as String? ?? 'C',
      startTime: (json['start_time'] as num?)?.toDouble() ?? 0.0,
      endTime: (json['end_time'] as num?)?.toDouble() ?? 1.0,
      duration: (json['duration'] as num?)?.toDouble() ?? 1.0,
      beat: (json['beat'] as num?)?.toInt() ?? 1,
      beatDuration: (json['beat_duration'] as num?)?.toDouble() ?? 1.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
      needsReview: json['needs_review'] as bool? ?? false,
      alternatives: (json['alternatives'] as List<dynamic>?)
              ?.map((e) => ChordCandidate.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() => {
        'root': root,
        'quality': quality,
        'bass': bass,
        'inversion': inversion,
        'display': display,
        'start_time': startTime,
        'end_time': endTime,
        'duration': duration,
        'beat': beat,
        'beat_duration': beatDuration,
        'confidence': confidence,
        'needs_review': needsReview,
        'alternatives': alternatives.map((e) => e.toJson()).toList(),
      };
}
