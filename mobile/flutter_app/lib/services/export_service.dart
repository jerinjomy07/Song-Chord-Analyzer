import 'dart:convert';
import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:share_plus/share_plus.dart';
import '../models/song_analysis.dart';

class ExportService {
  /// Generates a monospace TXT chord chart
  static String generateTxt(SongAnalysis song) {
    final buffer = StringBuffer();
    buffer.writeln('================================================================');
    buffer.writeln('${song.title.toUpperCase()} - CHORD CHART');
    buffer.writeln('Key: ${song.key.display} | Tempo: ${song.tempo.bpm.toStringAsFixed(1)} BPM | Meter: ${song.meter.display}');
    buffer.writeln('================================================================\n');

    for (final sec in song.sections) {
      buffer.writeln('--- ${sec.name} ---');
      var line = '';
      for (var i = 0; i < sec.bars.length; i++) {
        final bar = sec.bars[i];
        final barText = bar.chords.map((c) => c.display).join(' ');
        line += '| ${barText.padRight(12)}';
        if ((i + 1) % 4 == 0 || i == sec.bars.length - 1) {
          line += '|';
          buffer.writeln(line);
          line = '';
        }
      }
      buffer.writeln();
    }
    return buffer.toString();
  }

  /// Exports and shares as TXT file
  static Future<void> exportTxt(SongAnalysis song) async {
    final text = generateTxt(song);
    final tempDir = await getTemporaryDirectory();
    final sanitized = song.title.replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_');
    final file = File('${tempDir.path}/$sanitized-chords.txt');
    await file.writeAsString(text);
    await Share.shareXFiles([XFile(file.path)], text: '${song.title} Chord Chart');
  }

  /// Exports and shares complete structured JSON
  static Future<void> exportJson(SongAnalysis song) async {
    final jsonStr = const JsonEncoder.withIndent('  ').convert(song.toJson());
    final tempDir = await getTemporaryDirectory();
    final sanitized = song.title.replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_');
    final file = File('${tempDir.path}/$sanitized-analysis.json');
    await file.writeAsString(jsonStr);
    await Share.shareXFiles([XFile(file.path)], text: '${song.title} JSON Analysis');
  }

  /// Generates a PDF sheet music chart matching desktop ReportLab layout
  static Future<void> exportPdf(SongAnalysis song) async {
    final pdf = pw.Document();

    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(32),
        build: (context) => [
          pw.Header(
            level: 0,
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
              children: [
                pw.Text(
                  song.title,
                  style: pw.TextStyle(fontSize: 22, fontWeight: pw.FontWeight.bold),
                ),
                pw.Text(
                  'Song Chord Analyzer',
                  style: const pw.TextStyle(fontSize: 10, color: PdfColors.grey700),
                ),
              ],
            ),
          ),
          pw.Container(
            padding: const pw.EdgeInsets.symmetric(vertical: 8),
            decoration: const pw.BoxDecoration(
              border: pw.Border(bottom: pw.BorderSide(color: PdfColors.grey400)),
            ),
            child: pw.Row(
              mainAxisAlignment: pw.MainAxisAlignment.spaceAround,
              children: [
                pw.Text('Key: ${song.key.display}', style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
                pw.Text('Tempo: ${song.tempo.bpm.toStringAsFixed(0)} BPM', style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
                pw.Text('Time: ${song.meter.display}', style: pw.TextStyle(fontWeight: pw.FontWeight.bold)),
                if (song.transposeSemitones != 0)
                  pw.Text('Transposed: ${song.transposeSemitones > 0 ? "+" : ""}${song.transposeSemitones}', style: pw.TextStyle(color: PdfColors.indigo)),
              ],
            ),
          ),
          pw.SizedBox(height: 16),
          ...song.sections.map((sec) {
            return pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 16),
              child: pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                children: [
                  pw.Container(
                    padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                    decoration: pw.BoxDecoration(
                      color: PdfColors.indigo50,
                      borderRadius: pw.BorderRadius.circular(4),
                    ),
                    child: pw.Text(
                      sec.name,
                      style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold, color: PdfColors.indigo900),
                    ),
                  ),
                  pw.SizedBox(height: 6),
                  pw.Wrap(
                    spacing: 4,
                    runSpacing: 4,
                    children: sec.bars.map((bar) {
                      final chordNames = bar.chords.map((c) => c.display).join('  ');
                      return pw.Container(
                        width: 110,
                        padding: const pw.EdgeInsets.symmetric(horizontal: 6, vertical: 8),
                        decoration: pw.BoxDecoration(
                          border: pw.Border.all(color: PdfColors.grey400),
                          borderRadius: pw.BorderRadius.circular(4),
                        ),
                        child: pw.Column(
                          crossAxisAlignment: pw.CrossAxisAlignment.start,
                          children: [
                            pw.Text(
                              'Bar ${bar.barNumber}',
                              style: const pw.TextStyle(fontSize: 8, color: PdfColors.grey600),
                            ),
                            pw.SizedBox(height: 4),
                            pw.Text(
                              chordNames.isEmpty ? 'N' : chordNames,
                              style: pw.TextStyle(fontSize: 12, fontWeight: pw.FontWeight.bold),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );

    final tempDir = await getTemporaryDirectory();
    final sanitized = song.title.replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_');
    final file = File('${tempDir.path}/$sanitized-chart.pdf');
    await file.writeAsBytes(await pdf.save());
    await Share.shareXFiles([XFile(file.path)], text: '${song.title} PDF Chord Chart');
  }
}
