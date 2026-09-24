import 'bar.dart';

class MusicalSection {
  final String sectionId;
  String name;
  final double startTime;
  final double endTime;
  final int startBar;
  final int endBar;
  final List<Bar> bars;
  final bool isRepeated;
  final String? repeatOfSectionId;

  MusicalSection({
    required this.sectionId,
    required this.name,
    required this.startTime,
    required this.endTime,
    required this.startBar,
    required this.endBar,
    required this.bars,
    this.isRepeated = false,
    this.repeatOfSectionId,
  });

  factory MusicalSection.fromJson(Map<String, dynamic> json) {
    return MusicalSection(
      sectionId: json['section_id'] as String? ?? 'sec_0',
      name: json['name'] as String? ?? 'SECTION',
      startTime: (json['start_time'] as num?)?.toDouble() ?? 0.0,
      endTime: (json['end_time'] as num?)?.toDouble() ?? 0.0,
      startBar: (json['start_bar'] as num?)?.toInt() ?? 1,
      endBar: (json['end_bar'] as num?)?.toInt() ?? 1,
      bars: (json['bars'] as List<dynamic>?)
              ?.map((e) => Bar.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      isRepeated: json['is_repeated'] as bool? ?? false,
      repeatOfSectionId: json['repeat_of_section_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        'section_id': sectionId,
        'name': name,
        'start_time': startTime,
        'end_time': endTime,
        'start_bar': startBar,
        'end_bar': endBar,
        'bars': bars.map((e) => e.toJson()).toList(),
        'is_repeated': isRepeated,
        'repeat_of_section_id': repeatOfSectionId,
      };
}
