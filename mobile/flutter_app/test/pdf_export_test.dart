import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:song_chord_analyzer/models/song_analysis.dart';
import 'package:song_chord_analyzer/models/bar.dart';
import 'package:song_chord_analyzer/models/chord_prediction.dart';
import 'package:song_chord_analyzer/services/export_service.dart';

void main() {
  group('Mobile Musician-Grade PDF Export Tests', () {
    late SongAnalysis bekhayali;
    late SongAnalysis kaattu;

    setUpAll(() {
      final file = File('test/fixtures/bekhayali_golden_analysis.json');
      expect(file.existsSync(), isTrue);
      final json = jsonDecode(file.readAsStringSync()) as Map<String, dynamic>;
      bekhayali = SongAnalysis.fromJson(json);

      // Create Kaattu Thottappol test analysis fixture
      kaattu = SongAnalysis.fromJson({
        'id': 'kaattu-001',
        'title': 'Kaattu Thottappol',
        'schema_version': '1.0.0',
        'metadata': {
          'filename': 'kaattu.mp3',
          'duration': 180.0,
          'sample_rate': 44100,
          'channels': 2,
          'format': 'mp3',
          'file_size_bytes': 3500000,
          'file_hash': 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        },
        'pipeline_metadata': {
          'pipeline_version': '1.0.0',
          'model_name': 'BTC-Transformer',
        },
        'key': {
          'tonic': 'D',
          'mode': 'major',
          'display': 'D Major',
          'confidence': 0.95,
        },
        'tempo': {
          'bpm': 136.0,
          'confidence': 0.95,
          'is_estimated': false,
        },
        'meter': {
          'numerator': 7,
          'denominator': 8,
          'display': '7/8',
          'confidence': 0.95,
        },
        'beat_grid': {
          'bpm': 136.0,
          'beats': [0.0, 0.44, 0.88],
          'downbeats': [0.0],
        },
        'chords': [],
        'sections': [
          {
            'section_id': 'sec-intro',
            'name': 'INTRO',
            'start_time': 0.0,
            'end_time': 16.0,
            'start_bar': 0,
            'end_bar': 7,
            'bars': [
              {'bar_number': 0, 'start_time': 0.0, 'end_time': 2.0, 'chords': []},
              {'bar_number': 1, 'start_time': 2.0, 'end_time': 4.0, 'chords': []},
              {'bar_number': 2, 'start_time': 4.0, 'end_time': 6.0, 'chords': []},
              {'bar_number': 3, 'start_time': 6.0, 'end_time': 8.0, 'chords': []},
              {'bar_number': 4, 'start_time': 8.0, 'end_time': 10.0, 'chords': []},
              {'bar_number': 5, 'start_time': 10.0, 'end_time': 12.0, 'chords': []},
              {
                'bar_number': 6,
                'start_time': 12.0,
                'end_time': 14.0,
                'chords': [
                  {
                    'root': 'A',
                    'quality': 'sus4',
                    'bass': 'A',
                    'display': 'Asus4',
                    'start_time': 12.0,
                    'end_time': 13.0,
                    'duration': 1.0,
                    'confidence': 0.9,
                  },
                  {
                    'root': 'D',
                    'quality': 'maj',
                    'bass': 'D',
                    'display': 'D',
                    'start_time': 13.0,
                    'end_time': 14.0,
                    'duration': 1.0,
                    'confidence': 0.9,
                  },
                ],
              },
              {
                'bar_number': 7,
                'start_time': 14.0,
                'end_time': 16.0,
                'chords': [
                  {
                    'root': 'D',
                    'quality': 'maj',
                    'bass': 'D',
                    'display': 'D',
                    'start_time': 14.0,
                    'end_time': 16.0,
                    'duration': 2.0,
                    'confidence': 0.9,
                  },
                ],
              },
            ],
          },
          {
            'section_id': 'sec-a',
            'name': 'SECTION A',
            'start_time': 16.0,
            'end_time': 32.0,
            'start_bar': 8,
            'end_bar': 15,
            'bars': [
              {
                'bar_number': 8,
                'start_time': 16.0,
                'end_time': 18.0,
                'chords': [
                  {'root': 'D', 'quality': 'min', 'bass': 'D', 'display': 'Dm', 'start_time': 16.0, 'end_time': 18.0, 'duration': 2.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 9,
                'start_time': 18.0,
                'end_time': 20.0,
                'chords': [
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 18.0, 'end_time': 20.0, 'duration': 2.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 10,
                'start_time': 20.0,
                'end_time': 22.0,
                'chords': [
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 20.0, 'end_time': 21.0, 'duration': 1.0, 'confidence': 0.9},
                  {'root': 'D', 'quality': 'maj', 'bass': 'D', 'display': 'D', 'start_time': 21.0, 'end_time': 22.0, 'duration': 1.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 11,
                'start_time': 22.0,
                'end_time': 24.0,
                'chords': [
                  {'root': 'D', 'quality': 'maj', 'bass': 'D', 'display': 'D', 'start_time': 22.0, 'end_time': 24.0, 'duration': 2.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 12,
                'start_time': 24.0,
                'end_time': 26.0,
                'chords': [
                  {'root': 'D', 'quality': 'min', 'bass': 'D', 'display': 'Dm', 'start_time': 24.0, 'end_time': 24.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 24.5, 'end_time': 25.0, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'D', 'quality': 'min', 'bass': 'D', 'display': 'Dm', 'start_time': 25.0, 'end_time': 25.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 25.5, 'end_time': 26.0, 'duration': 0.5, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 13,
                'start_time': 26.0,
                'end_time': 28.0,
                'chords': [
                  {'root': 'D', 'quality': 'min', 'bass': 'D', 'display': 'Dm', 'start_time': 26.0, 'end_time': 27.0, 'duration': 1.0, 'confidence': 0.9},
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 27.0, 'end_time': 28.0, 'duration': 1.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 14,
                'start_time': 28.0,
                'end_time': 30.0,
                'chords': [
                  {'root': 'A', 'quality': 'sus4', 'bass': 'A', 'display': 'Asus4', 'start_time': 28.0, 'end_time': 29.0, 'duration': 1.0, 'confidence': 0.9},
                  {'root': 'D', 'quality': 'maj', 'bass': 'D', 'display': 'D', 'start_time': 29.0, 'end_time': 30.0, 'duration': 1.0, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 15,
                'start_time': 30.0,
                'end_time': 32.0,
                'chords': [
                  {'root': 'D', 'quality': 'maj', 'bass': 'D', 'display': 'D', 'start_time': 30.0, 'end_time': 32.0, 'duration': 2.0, 'confidence': 0.9},
                ],
              },
            ],
          },
          {
            'section_id': 'sec-b',
            'name': 'SECTION B',
            'start_time': 32.0,
            'end_time': 48.0,
            'start_bar': 16,
            'end_bar': 23,
            'bars': [
              {
                'bar_number': 16,
                'start_time': 32.0,
                'end_time': 34.0,
                'chords': [
                  {'root': 'D', 'quality': 'min', 'bass': 'D', 'display': 'Dm', 'start_time': 32.0, 'end_time': 32.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'sus2', 'bass': 'G', 'display': 'Gsus2', 'start_time': 32.6, 'end_time': 33.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'maj', 'bass': 'G', 'display': 'G', 'start_time': 33.3, 'end_time': 34.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 17,
                'start_time': 34.0,
                'end_time': 36.0,
                'chords': [
                  {'root': 'G', 'quality': 'maj', 'bass': 'G', 'display': 'G', 'start_time': 34.0, 'end_time': 34.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'sus2', 'bass': 'G', 'display': 'Gsus2', 'start_time': 34.6, 'end_time': 35.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 35.3, 'end_time': 36.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 18,
                'start_time': 36.0,
                'end_time': 38.0,
                'chords': [
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 36.0, 'end_time': 36.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'C', 'quality': 'maj', 'bass': 'C', 'display': 'C', 'start_time': 36.6, 'end_time': 37.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 37.3, 'end_time': 38.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 19,
                'start_time': 38.0,
                'end_time': 40.0,
                'chords': [
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 38.0, 'end_time': 38.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'C', 'quality': 'maj', 'bass': 'C', 'display': 'C', 'start_time': 38.6, 'end_time': 39.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'A#', 'quality': 'maj', 'bass': 'G', 'display': 'A#/G', 'start_time': 39.3, 'end_time': 40.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 20,
                'start_time': 40.0,
                'end_time': 42.0,
                'chords': [
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 40.0, 'end_time': 40.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'C', 'quality': 'maj', 'bass': 'F', 'display': 'C/F', 'start_time': 40.6, 'end_time': 41.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'C', 'quality': 'maj', 'bass': 'C', 'display': 'C', 'start_time': 41.3, 'end_time': 42.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 21,
                'start_time': 42.0,
                'end_time': 44.0,
                'chords': [
                  {'root': 'B', 'quality': 'min', 'bass': 'B', 'display': 'Bm', 'start_time': 42.0, 'end_time': 42.6, 'duration': 0.6, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'maj', 'bass': 'B', 'display': 'G/B', 'start_time': 42.6, 'end_time': 43.3, 'duration': 0.7, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'maj', 'bass': 'G', 'display': 'G', 'start_time': 43.3, 'end_time': 44.0, 'duration': 0.7, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 22,
                'start_time': 44.0,
                'end_time': 46.0,
                'chords': [
                  {'root': 'A#', 'quality': 'maj', 'bass': 'A#', 'display': 'A#', 'start_time': 44.0, 'end_time': 44.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'F', 'quality': 'maj', 'bass': 'A#', 'display': 'F/A#', 'start_time': 44.5, 'end_time': 45.0, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'C', 'quality': 'maj', 'bass': 'C', 'display': 'C', 'start_time': 45.0, 'end_time': 45.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'G', 'quality': 'min', 'bass': 'G', 'display': 'Gm', 'start_time': 45.5, 'end_time': 46.0, 'duration': 0.5, 'confidence': 0.9},
                ],
              },
              {
                'bar_number': 23,
                'start_time': 46.0,
                'end_time': 48.0,
                'chords': [
                  {'root': 'G', 'quality': 'min', 'bass': 'D', 'display': 'Gm/D', 'start_time': 46.0, 'end_time': 46.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'F', 'quality': 'maj', 'bass': 'A', 'display': 'F/A', 'start_time': 46.5, 'end_time': 47.0, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'F', 'quality': 'maj', 'bass': 'E', 'display': 'F/E', 'start_time': 47.0, 'end_time': 47.5, 'duration': 0.5, 'confidence': 0.9},
                  {'root': 'D', 'quality': 'maj', 'bass': 'D', 'display': 'D', 'start_time': 47.5, 'end_time': 48.0, 'duration': 0.5, 'confidence': 0.9},
                ],
              },
            ],
          },
        ],
      });
    });

    test('1. formatBarChords formats single chords, multi-chords, and preserves slash chords', () {
      final emptyBar = Bar(barNumber: 0, startTime: 0, endTime: 2, chords: []);
      expect(ExportService.formatBarChords(emptyBar), equals('N'));

      final slashBar = Bar(
        barNumber: 1,
        startTime: 0,
        endTime: 2,
        chords: [
          ChordPrediction(root: 'A', quality: 'maj', bass: 'C#', display: 'A/C#', startTime: 0, endTime: 2, duration: 2, confidence: 0.9),
        ],
      );
      expect(ExportService.formatBarChords(slashBar), equals('A/C#'));

      final multiBar = Bar(
        barNumber: 2,
        startTime: 0,
        endTime: 2,
        chords: [
          ChordPrediction(root: 'A', quality: 'sus4', bass: 'A', display: 'Asus4', startTime: 0, endTime: 1, duration: 1, confidence: 0.9),
          ChordPrediction(root: 'D', quality: 'maj', bass: 'D', display: 'D', startTime: 1, endTime: 2, duration: 1, confidence: 0.9),
        ],
      );
      expect(ExportService.formatBarChords(multiBar), equals('Asus4  D'));
    });

    test('2. Generates valid PDF bytes for Kaattu Thottappol and saves test file', () async {
      final pdfBytes = await ExportService.generatePdfBytes(kaattu);
      expect(pdfBytes, isNotNull);
      expect(pdfBytes.length, greaterThan(1000));
      // PDF header magic bytes %PDF
      expect(utf8.decode(pdfBytes.sublist(0, 4)), equals('%PDF'));

      final outFile = File('test_kaattu_exported.pdf');
      await outFile.writeAsBytes(pdfBytes);
      expect(outFile.existsSync(), isTrue);
    });

    test('3. Generates multi-page PDF for full-length song Bekhayali', () async {
      final pdfBytes = await ExportService.generatePdfBytes(bekhayali);
      expect(pdfBytes, isNotNull);
      expect(pdfBytes.length, greaterThan(2000));
      expect(utf8.decode(pdfBytes.sublist(0, 4)), equals('%PDF'));

      final outFile = File('test_bekhayali_exported.pdf');
      await outFile.writeAsBytes(pdfBytes);
      expect(outFile.existsSync(), isTrue);
    });
  });
}
