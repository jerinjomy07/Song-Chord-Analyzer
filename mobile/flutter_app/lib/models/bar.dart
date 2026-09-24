import 'chord_prediction.dart';

class Bar {
  final int barNumber;
  final double startTime;
  final double endTime;
  final int beats;
  final String timeSignature;
  String display;
  List<ChordPrediction> chords;

  Bar({
    required this.barNumber,
    required this.startTime,
    required this.endTime,
    this.beats = 4,
    this.timeSignature = '4/4',
    this.display = '',
    required this.chords,
  });

  factory Bar.fromJson(Map<String, dynamic> json) {
    return Bar(
      barNumber: (json['bar_number'] as num?)?.toInt() ?? 1,
      startTime: (json['start_time'] as num?)?.toDouble() ?? 0.0,
      endTime: (json['end_time'] as num?)?.toDouble() ?? 2.0,
      beats: (json['beats'] as num?)?.toInt() ?? 4,
      timeSignature: json['time_signature'] as String? ?? '4/4',
      display: json['display'] as String? ?? '',
      chords: (json['chords'] as List<dynamic>?)
              ?.map((e) => ChordPrediction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  Map<String, dynamic> toJson() => {
        'bar_number': barNumber,
        'start_time': startTime,
        'end_time': endTime,
        'beats': beats,
        'time_signature': timeSignature,
        'display': display,
        'chords': chords.map((e) => e.toJson()).toList(),
      };
}
