import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:path_provider/path_provider.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;
import 'package:share_plus/share_plus.dart';
import '../models/song_analysis.dart';
import '../models/musical_section.dart';
import '../models/bar.dart';

class ExportService {
  /// Formats chords inside a single bar measure into compact lead-sheet text
  /// with slash chords intact and multiple chord changes separated by spaces.
  static String formatBarChords(Bar bar, {String emptyChar = 'N'}) {
    final validChords = bar.chords
        .where((c) => c.display != 'N' && c.display.trim().isNotEmpty)
        .toList();
    if (validChords.isEmpty) {
      return emptyChar;
    }

    // Deduplicate consecutive identical chord display labels
    final List<String> collapsed = [];
    for (int i = 0; i < validChords.length; i++) {
      final disp = validChords[i].display;
      if (collapsed.isEmpty) {
        collapsed.add(disp);
      } else {
        final prev = validChords[i - 1];
        // Refine unslashed chord if immediately followed by same harmony with slash bass (e.g. Gm -> Gm/F)
        if (validChords[i].root == prev.root &&
            validChords[i].quality == prev.quality &&
            !prev.display.contains('/') &&
            disp.contains('/')) {
          collapsed[collapsed.length - 1] = disp;
        } else if (disp != collapsed.last) {
          collapsed.add(disp);
        }
      }
    }

    if (collapsed.isEmpty) {
      return emptyChar;
    }
    return collapsed.join('  ');
  }

  /// Groups bars in a section into lines of measures using dynamic width calculation.
  /// Prevents line overflow while maintaining intact musical measures and standard 4-bar systems.
  static List<List<String>> formatSectionLines(
    MusicalSection sec, {
    double availableWidth = 523.0,
    double chordFontSize = 13.0,
    int maxBarsPerLine = 4,
    PdfFont? font,
  }) {
    final List<List<String>> lines = [];
    List<String> currentLine = [];

    for (final bar in sec.bars) {
      final barStr = formatBarChords(bar);

      if (currentLine.isEmpty) {
        currentLine.add(barStr);
      } else {
        final candidate = [...currentLine, barStr];
        bool fits = candidate.length <= maxBarsPerLine;

        if (fits && font != null) {
          final candidateText = '| ${candidate.join(' | ')} |';
          final width = font.stringMetrics(candidateText).width * chordFontSize;
          if (width > availableWidth) {
            fits = false;
          }
        }

        if (fits) {
          currentLine.add(barStr);
        } else {
          lines.add(currentLine);
          currentLine = [barStr];
        }
      }
    }

    if (currentLine.isNotEmpty) {
      lines.add(currentLine);
    }
    return lines;
  }

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

  /// Generates a musician-friendly printable chord sheet PDF matching the desktop reference lead sheet format:
  /// - Clean title and compact horizontal metadata row (Key, Tempo, Meter, Transpose)
  /// - Visually distinct section headings (INTRO:, VERSE:, CHORUS:, etc.)
  /// - Bars formatted with vertical separators: | D | F#m | A | E |
  /// - Multiple chords inside a bar separated by spaces: | Asus4  D |
  /// - Slash chords preserved intact: | A/C# | D/F# | G/B |
  /// - Automatic line wrapping fitting complete intact bars to available page width
  /// - Section header + first chord line kept together across page breaks
  /// - Multi-page running header and footer
  static Future<pw.Document> generatePdfDocument(SongAnalysis song) async {
    final pdf = pw.Document();

    final fontBold = pw.Font.helveticaBold();
    final fontRegular = pw.Font.helvetica();

    // Metric calculation font (accessed via a temporary dummy PdfDocument)
    final dummyPdfDoc = PdfDocument();
    final pdfFont = PdfFont.helveticaBold(dummyPdfDoc);

    const double pageMargin = 36.0;
    const double availableWidth = 595.275 - (pageMargin * 2); // 523.275 pt
    const double chordFontSize = 13.0;

    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: const pw.EdgeInsets.all(pageMargin),
        header: (context) {
          if (context.pageNumber > 1) {
            return pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 12),
              padding: const pw.EdgeInsets.only(bottom: 4),
              decoration: const pw.BoxDecoration(
                border: pw.Border(
                  bottom: pw.BorderSide(color: PdfColors.grey400, width: 0.5),
                ),
              ),
              child: pw.Row(
                mainAxisAlignment: pw.MainAxisAlignment.spaceBetween,
                children: [
                  pw.Text(
                    song.title,
                    style: pw.TextStyle(
                      font: fontBold,
                      fontSize: 9,
                      color: PdfColors.grey800,
                    ),
                  ),
                  pw.Text(
                    'Key: ${song.key.display}  |  Tempo: ${song.tempo.bpm.toStringAsFixed(0)} BPM  |  Time: ${song.meter.display}',
                    style: pw.TextStyle(
                      font: fontRegular,
                      fontSize: 8,
                      color: PdfColors.grey600,
                    ),
                  ),
                ],
              ),
            );
          }
          return pw.SizedBox.shrink();
        },
        footer: (context) {
          return pw.Container(
            margin: const pw.EdgeInsets.only(top: 8),
            alignment: pw.Alignment.centerRight,
            child: pw.Text(
              'Page ${context.pageNumber} of ${context.pagesCount}',
              style: pw.TextStyle(
                font: fontRegular,
                fontSize: 8,
                color: PdfColors.grey600,
              ),
            ),
          );
        },
        build: (context) {
          final List<pw.Widget> widgets = [];

          // 1. Song Title Header
          widgets.add(
            pw.Text(
              song.title,
              style: pw.TextStyle(
                font: fontBold,
                fontSize: 20,
                fontWeight: pw.FontWeight.bold,
              ),
            ),
          );
          widgets.add(pw.SizedBox(height: 4));

          // 2. Compact Horizontal Metadata Line
          widgets.add(
            pw.Row(
              children: [
                pw.Text(
                  'Key: ${song.key.display}',
                  style: pw.TextStyle(font: fontBold, fontSize: 10),
                ),
                pw.SizedBox(width: 24),
                pw.Text(
                  'Tempo: ${song.tempo.bpm.toStringAsFixed(0)} BPM',
                  style: pw.TextStyle(font: fontBold, fontSize: 10),
                ),
                pw.SizedBox(width: 24),
                pw.Text(
                  'Time: ${song.meter.display}',
                  style: pw.TextStyle(font: fontBold, fontSize: 10),
                ),
                if (song.transposeSemitones != 0) ...[
                  pw.SizedBox(width: 24),
                  pw.Text(
                    'Transposed: ${song.transposeSemitones > 0 ? "+" : ""}${song.transposeSemitones}',
                    style: pw.TextStyle(
                      font: fontBold,
                      fontSize: 10,
                      color: PdfColors.indigo700,
                    ),
                  ),
                ],
              ],
            ),
          );
          widgets.add(pw.SizedBox(height: 4));
          widgets.add(pw.Divider(thickness: 0.8, color: PdfColors.grey400));
          widgets.add(pw.SizedBox(height: 10));

          // 3. Sections
          for (final sec in song.sections) {
            final rawName = sec.name.trim();
            final displayName = rawName.toUpperCase().endsWith(':')
                ? rawName.toUpperCase()
                : '${rawName.toUpperCase()}:';

            final lines = formatSectionLines(
              sec,
              availableWidth: availableWidth,
              chordFontSize: chordFontSize,
              maxBarsPerLine: 4,
              font: pdfFont,
            );

            if (lines.isEmpty) continue;

            final sectionHeaderWidget = pw.Container(
              margin: const pw.EdgeInsets.only(top: 6, bottom: 2),
              padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              color: PdfColors.yellow100,
              child: pw.Text(
                displayName,
                style: pw.TextStyle(
                  font: fontBold,
                  fontSize: 11,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
            );

            final chordTextStyle = pw.TextStyle(
              font: fontBold,
              fontSize: chordFontSize,
              lineSpacing: 1.2,
            );

            // Bind section heading + first chord line in a single non-splittable Column
            // so section heading is never orphaned at the bottom of a page
            widgets.add(
              pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                mainAxisSize: pw.MainAxisSize.min,
                children: [
                  sectionHeaderWidget,
                  pw.SizedBox(height: 3),
                  pw.Text('| ${lines.first.join(' | ')} |', style: chordTextStyle),
                ],
              ),
            );

            // Subsequent chord lines in the section flow naturally
            for (int i = 1; i < lines.length; i++) {
              widgets.add(pw.SizedBox(height: 3));
              widgets.add(
                pw.Text('| ${lines[i].join(' | ')} |', style: chordTextStyle),
              );
            }

            widgets.add(pw.SizedBox(height: 8));
          }

          return widgets;
        },
      ),
    );

    return pdf;
  }

  /// Generates the raw PDF bytes for testing or exporting
  static Future<Uint8List> generatePdfBytes(SongAnalysis song) async {
    final doc = await generatePdfDocument(song);
    return doc.save();
  }

  /// Exports and shares the musician-grade PDF chord chart
  static Future<void> exportPdf(SongAnalysis song) async {
    final pdfBytes = await generatePdfBytes(song);
    final tempDir = await getTemporaryDirectory();
    final sanitized = song.title.replaceAll(RegExp(r'[^a-zA-Z0-9_\-]'), '_');
    final file = File('${tempDir.path}/$sanitized-chart.pdf');
    await file.writeAsBytes(pdfBytes);
    await Share.shareXFiles([XFile(file.path)], text: '${song.title} PDF Chord Chart');
  }
}
