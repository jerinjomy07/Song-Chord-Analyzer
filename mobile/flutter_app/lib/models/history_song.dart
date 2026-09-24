class HistorySong {
  final String id;
  String title;
  final String originalFilename;
  final String fileHash;
  final double duration;
  final String format;
  final String keyDisplay;
  final String keyMode;
  final double bpm;
  final String timeSignature;
  int transposeValue;
  bool isFavorite;
  final String createdAt;
  String updatedAt;
  String lastOpenedAt;
  final int editCount;
  final String? localAudioPath;
  final String? sourceType;

  HistorySong({
    required this.id,
    required this.title,
    required this.originalFilename,
    required this.fileHash,
    required this.duration,
    required this.format,
    required this.keyDisplay,
    required this.keyMode,
    required this.bpm,
    required this.timeSignature,
    this.transposeValue = 0,
    this.isFavorite = false,
    required this.createdAt,
    required this.updatedAt,
    required this.lastOpenedAt,
    this.editCount = 0,
    this.localAudioPath,
    this.sourceType = 'local',
  });

  factory HistorySong.fromMap(Map<String, dynamic> map) {
    return HistorySong(
      id: map['id'] as String,
      title: map['title'] as String? ?? 'Untitled Song',
      originalFilename: map['original_filename'] as String? ?? '',
      fileHash: map['file_hash'] as String? ?? '',
      duration: (map['duration'] as num?)?.toDouble() ?? 0.0,
      format: map['format'] as String? ?? 'mp3',
      keyDisplay: map['key_display'] as String? ?? 'C Major',
      keyMode: map['key_mode'] as String? ?? 'major',
      bpm: (map['bpm'] as num?)?.toDouble() ?? 120.0,
      timeSignature: map['time_signature'] as String? ?? '4/4',
      transposeValue: (map['transpose_value'] as num?)?.toInt() ?? 0,
      isFavorite: (map['is_favorite'] == 1 || map['is_favorite'] == true),
      createdAt: map['created_at'] as String? ?? '',
      updatedAt: map['updated_at'] as String? ?? '',
      lastOpenedAt: map['last_opened_at'] as String? ?? '',
      editCount: (map['edit_count'] as num?)?.toInt() ?? 0,
      localAudioPath: map['local_audio_path'] as String?,
      sourceType: map['source_type'] as String? ?? 'local',
    );
  }

  Map<String, dynamic> toMap() => {
        'id': id,
        'title': title,
        'original_filename': originalFilename,
        'file_hash': fileHash,
        'duration': duration,
        'format': format,
        'key_display': keyDisplay,
        'key_mode': keyMode,
        'bpm': bpm,
        'time_signature': timeSignature,
        'transpose_value': transposeValue,
        'is_favorite': isFavorite ? 1 : 0,
        'created_at': createdAt,
        'updated_at': updatedAt,
        'last_opened_at': lastOpenedAt,
        'edit_count': editCount,
        'local_audio_path': localAudioPath,
        'source_type': sourceType,
      };
}
