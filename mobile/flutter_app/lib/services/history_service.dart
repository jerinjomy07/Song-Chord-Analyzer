import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:path_provider/path_provider.dart';
import 'package:sqflite/sqflite.dart';
import '../models/history_song.dart';
import '../models/song_analysis.dart';

class HistoryService {
  static Database? _database;

  static Future<Database> get database async {
    if (_database != null) return _database!;
    _database = await _initDb();
    return _database!;
  }

  static Future<Database> _initDb() async {
    final docsDir = await getApplicationDocumentsDirectory();
    final dbPath = p.join(docsDir.path, 'song_chord_analyzer.db');

    return await openDatabase(
      dbPath,
      version: 1,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE songs (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_hash TEXT,
            duration REAL NOT NULL,
            format TEXT NOT NULL,
            key_display TEXT NOT NULL,
            key_mode TEXT NOT NULL,
            bpm REAL NOT NULL,
            time_signature TEXT NOT NULL,
            transpose_value INTEGER DEFAULT 0,
            is_favorite INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_opened_at TEXT NOT NULL,
            edit_count INTEGER DEFAULT 0,
            local_audio_path TEXT,
            source_type TEXT DEFAULT 'local',
            analysis_json TEXT NOT NULL
          )
        ''');

        await db.execute('''
          CREATE TABLE user_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            song_id TEXT NOT NULL,
            chord_index INTEGER NOT NULL,
            original_chord TEXT NOT NULL,
            corrected_chord TEXT NOT NULL,
            bar INTEGER,
            beat INTEGER,
            confidence REAL,
            created_at TEXT NOT NULL
          )
        ''');
      },
    );
  }

  static Future<void> saveAnalysis({
    required SongAnalysis analysis,
    required File sourceAudio,
  }) async {
    final db = await database;
    final docsDir = await getApplicationDocumentsDirectory();
    final libraryDir = Directory(p.join(docsDir.path, 'library', analysis.id));
    if (!libraryDir.existsSync()) {
      libraryDir.createSync(parents: true);
    }

    final ext = p.extension(sourceAudio.path);
    final targetAudio = File(p.join(libraryDir.path, 'audio$ext'));
    if (!targetAudio.existsSync()) {
      await sourceAudio.copy(targetAudio.path);
    }
    analysis.localAudioPath = targetAudio.path;

    final now = DateTime.now().toIso8601String();
    final existing = await db.query('songs', where: 'id = ?', whereArgs: [analysis.id]);

    final Map<String, dynamic> row = {
      'id': analysis.id,
      'title': analysis.title,
      'original_filename': analysis.metadata.filename,
      'file_hash': analysis.metadata.fileHash,
      'duration': analysis.metadata.duration,
      'format': analysis.metadata.format,
      'key_display': analysis.key.display,
      'key_mode': analysis.key.mode,
      'bpm': analysis.tempo.bpm,
      'time_signature': analysis.meter.display,
      'transpose_value': analysis.transposeSemitones,
      'updated_at': now,
      'last_opened_at': now,
      'local_audio_path': targetAudio.path,
      'source_type': 'local',
      'analysis_json': jsonEncode(analysis.toJson()),
    };

    if (existing.isEmpty) {
      row['created_at'] = now;
      row['is_favorite'] = 0;
      row['edit_count'] = 0;
      await db.insert('songs', row);
    } else {
      await db.update('songs', row, where: 'id = ?', whereArgs: [analysis.id]);
    }
  }

  static Future<List<HistorySong>> getSongs({
    String? searchQuery,
    String sortBy = 'last_opened_at',
    bool ascending = false,
  }) async {
    final db = await database;
    String? where;
    List<dynamic>? whereArgs;

    if (searchQuery != null && searchQuery.trim().isNotEmpty) {
      where = 'title LIKE ? OR key_display LIKE ? OR original_filename LIKE ?';
      final q = '%${searchQuery.trim()}%';
      whereArgs = [q, q, q];
    }

    final orderDirection = ascending ? 'ASC' : 'DESC';
    final rows = await db.query(
      'songs',
      where: where,
      whereArgs: whereArgs,
      orderBy: '$sortBy $orderDirection',
    );

    return rows.map((r) => HistorySong.fromMap(r)).toList();
  }

  static Future<SongAnalysis?> loadAnalysis(String songId) async {
    final db = await database;
    final rows = await db.query('songs', where: 'id = ?', whereArgs: [songId]);
    if (rows.isEmpty) return null;

    final row = rows.first;
    final jsonStr = row['analysis_json'] as String;
    final data = jsonDecode(jsonStr) as Map<String, dynamic>;
    final analysis = SongAnalysis.fromJson(data);
    analysis.localAudioPath = row['local_audio_path'] as String?;

    // Update last_opened_at
    await db.update(
      'songs',
      {'last_opened_at': DateTime.now().toIso8601String()},
      where: 'id = ?',
      whereArgs: [songId],
    );

    return analysis;
  }

  static Future<void> updateSongTitle(String songId, String newTitle) async {
    final db = await database;
    final analysis = await loadAnalysis(songId);
    if (analysis != null) {
      analysis.title = newTitle;
      await db.update(
        'songs',
        {
          'title': newTitle,
          'updated_at': DateTime.now().toIso8601String(),
          'analysis_json': jsonEncode(analysis.toJson()),
        },
        where: 'id = ?',
        whereArgs: [songId],
      );
    }
  }

  static Future<void> toggleFavorite(String songId, bool isFavorite) async {
    final db = await database;
    await db.update(
      'songs',
      {'is_favorite': isFavorite ? 1 : 0},
      where: 'id = ?',
      whereArgs: [songId],
    );
  }

  static Future<void> deleteSong(String songId) async {
    final db = await database;
    final docsDir = await getApplicationDocumentsDirectory();
    final songDir = Directory(p.join(docsDir.path, 'library', songId));
    if (songDir.existsSync()) {
      songDir.deleteSync(recursive: true);
    }
    await db.delete('songs', where: 'id = ?', whereArgs: [songId]);
    await db.delete('user_corrections', where: 'song_id = ?', whereArgs: [songId]);
  }

  static Future<void> recordCorrection({
    required String songId,
    required int chordIndex,
    required String originalChord,
    required String correctedChord,
    int? bar,
    int? beat,
    double? confidence,
  }) async {
    final db = await database;
    await db.insert('user_corrections', {
      'song_id': songId,
      'chord_index': chordIndex,
      'original_chord': originalChord,
      'corrected_chord': correctedChord,
      'bar': bar,
      'beat': beat,
      'confidence': confidence,
      'created_at': DateTime.now().toIso8601String(),
    });
  }
}
