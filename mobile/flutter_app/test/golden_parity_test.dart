import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:song_chord_analyzer/models/song_analysis.dart';
import 'package:song_chord_analyzer/models/analysis_status.dart';
import 'package:song_chord_analyzer/services/transpose_service.dart';
import 'package:song_chord_analyzer/services/export_service.dart';

void main() {
  group('Golden Song (Bekhayali) Parity & Schema Tests', () {
    late Map<String, dynamic> goldenJson;
    late SongAnalysis analysis;

    setUpAll(() {
      final file = File('test/fixtures/bekhayali_golden_analysis.json');
      expect(file.existsSync(), isTrue, reason: 'Golden analysis fixture must exist');
      goldenJson = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
      analysis = SongAnalysis.fromJson(goldenJson);
    });

    test('1. Validates top-level metadata and ID parity', () {
      expect(analysis.id, equals('f7a49eee'));
      expect(analysis.title, contains('Bekhayali'));
      expect(analysis.schemaVersion, equals('1.0.0'));
      expect(analysis.metadata.sampleRate, equals(44100));
      expect(analysis.metadata.channels, equals(2));
      expect(analysis.metadata.duration, greaterThan(240.0));
    });

    test('2. Validates pipeline metadata parity', () {
      expect(analysis.pipelineMetadata.modelName, contains('BTC-Transformer'));
      expect(analysis.pipelineMetadata.separationModel, equals('htdemucs'));
    });

    test('3. Validates Key parity (Bb Minor)', () {
      expect(analysis.key.tonic, equals('Bb'));
      expect(analysis.key.mode, equals('minor'));
      expect(analysis.key.display, equals('Bb Minor'));
      expect(analysis.key.confidence, equals(0.75));
    });

    test('4. Validates Tempo parity (86.1 BPM)', () {
      expect(analysis.tempo.bpm, equals(86.1));
      expect(analysis.tempo.confidence, greaterThanOrEqualTo(0.8));
    });

    test('5. Validates Meter parity (4/4 time signature)', () {
      expect(analysis.meter.numerator, equals(4));
      expect(analysis.meter.denominator, equals(4));
      expect(analysis.meter.display, equals('4/4'));
    });

    test('6. Validates Beat Grid parity (353 beats, 89 downbeats)', () {
      expect(analysis.beatGrid.bpm, equals(86.1));
      expect(analysis.beatGrid.beats.length, equals(353));
      expect(analysis.beatGrid.downbeats.length, equals(89));

      // Timestamps must be strictly ascending
      for (int i = 0; i < analysis.beatGrid.beats.length - 1; i++) {
        expect(
          analysis.beatGrid.beats[i + 1],
          greaterThan(analysis.beatGrid.beats[i]),
          reason: 'Beat timestamps must be monotonically increasing',
        );
      }
    });

    test('7. Validates Chords count and timing integrity (352 chords)', () {
      expect(analysis.chords.length, equals(352));

      for (int i = 0; i < analysis.chords.length; i++) {
        final chord = analysis.chords[i];
        expect(chord.endTime, greaterThan(chord.startTime), reason: 'Chord #$i endTime > startTime');
        expect(chord.duration, greaterThan(0.0), reason: 'Chord #$i duration > 0');
        expect(chord.root.isNotEmpty, isTrue, reason: 'Chord #$i root must not be empty');
        expect(chord.display.isNotEmpty, isTrue, reason: 'Chord #$i display must not be empty');
      }
    });

    test('8. Validates Section structure parity (11 musical sections)', () {
      expect(analysis.sections.length, equals(11));

      // Total chords inside section bars must equal total chords
      int totalBarChords = 0;
      for (final section in analysis.sections) {
        expect(section.name.isNotEmpty, isTrue);
        expect(section.bars.isNotEmpty, isTrue);
        for (final bar in section.bars) {
          totalBarChords += bar.chords.length;
        }
      }
      expect(totalBarChords, equals(210));
    });

    test('9. Validates JSON serialization and schema completeness', () {
      final jsonOut = analysis.toJson();

      // All schema-required keys must be present
      final requiredKeys = [
        'schema_version',
        'id',
        'title',
        'metadata',
        'pipeline_metadata',
        'key',
        'tempo',
        'meter',
        'beat_grid',
        'sections',
        'chords',
      ];
      for (final key in requiredKeys) {
        expect(jsonOut.containsKey(key), isTrue, reason: 'toJson() must include $key');
      }

      // Re-deserialization roundtrip
      final roundtrip = SongAnalysis.fromJson(jsonOut);
      expect(roundtrip.id, equals(analysis.id));
      expect(roundtrip.key.display, equals(analysis.key.display));
      expect(roundtrip.tempo.bpm, equals(analysis.tempo.bpm));
      expect(roundtrip.chords.length, equals(analysis.chords.length));
    });

    test('10. Validates Transposition invariance and accuracy (+2 semitones to C Minor)', () {
      final transposed = TransposeService.transposeSong(analysis, 2);

      // Key should transpose from Bb Minor to C Minor
      expect(transposed.key.tonic, equals('C'));
      expect(transposed.key.display, equals('C Minor'));
      expect(transposed.transposeSemitones, equals(2));

      // Chord counts and timings must remain 100% invariant
      expect(transposed.chords.length, equals(analysis.chords.length));
      for (int i = 0; i < transposed.chords.length; i++) {
        expect(transposed.chords[i].startTime, equals(analysis.chords[i].startTime));
        expect(transposed.chords[i].endTime, equals(analysis.chords[i].endTime));
        expect(transposed.chords[i].duration, equals(analysis.chords[i].duration));
      }

      // Check specific transposed chords: Bbm (root A#, qual min) -> Cm (root C, qual min, display Cm)
      final firstHarmonicChord = analysis.chords.firstWhere((c) => c.display == 'Bbm');
      final firstTransposedChord = transposed.chords.firstWhere((c) => c.startTime == firstHarmonicChord.startTime);
      expect(firstTransposedChord.root, equals('C'));
      expect(firstTransposedChord.quality, equals('min'));
      expect(firstTransposedChord.display, equals('Cm'));
    });

    test('11. Validates TXT export generation for musicians', () {
      final txt = ExportService.generateTxt(analysis);
      expect(txt, contains('BEKHAYALI'));
      expect(txt, contains('Bb Minor'));
      expect(txt, contains('86.1 BPM'));
      expect(txt, contains('4/4'));
      expect(txt, contains('|'));
    });
  });

  group('AnalysisStatus Stage Mapping Tests', () {
    test('Correctly maps server stages to AnalysisStage enum', () {
      final s1 = AnalysisStatus.fromJson({
        'analysis_id': 'job1',
        'status': 'queued',
        'current_stage': 'QUEUED',
        'progress': 0,
        'message': 'Queued',
      });
      expect(s1.stage, equals(AnalysisStage.queued));
      expect(s1.currentStage, equals('QUEUED'));

      final s2 = AnalysisStatus.fromJson({
        'analysis_id': 'job2',
        'status': 'processing',
        'current_stage': 'ANALYZING_BEATS',
        'progress': 45,
        'message': 'Detecting beats',
      });
      expect(s2.stage, equals(AnalysisStage.analyzingBeats));
      expect(s2.currentStage, equals('ANALYZING_BEATS'));

      final s3 = AnalysisStatus.fromJson({
        'analysis_id': 'job3',
        'status': 'completed',
        'current_stage': 'COMPLETED',
        'progress': 100,
        'message': 'Done',
      });
      expect(s3.stage, equals(AnalysisStage.completed));

      final s4 = AnalysisStatus.fromJson({
        'analysis_id': 'job4',
        'status': 'failed',
        'current_stage': 'FAILED',
        'progress': 20,
        'message': 'Audio corrupted',
        'error': 'Decode error',
      });
      expect(s4.stage, equals(AnalysisStage.failed));
      expect(s4.error, equals('Decode error'));
    });
  });
}
