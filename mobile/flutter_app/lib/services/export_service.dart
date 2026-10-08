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

/// Configuration profile for adaptive one-page PDF fitting
class PdfLayoutProfile {
  final double pageMargin;
  final double titleFontSize;
  final double metaFontSize;
  final double sectionFontSize;
  final double chordFontSize;
  final double chordLineSpacing;
  final double sectionSpacing;
  final double sectionHeaderTopMargin;
  final double headerBottomSpacing;
  final String chordSeparator;

  const PdfLayoutProfile({
    required this.pageMargin,
    required this.titleFontSize,
    required this.metaFontSize,
    required this.sectionFontSize,
    required this.chordFontSize,
    required this.chordLineSpacing,
    required this.sectionSpacing,
    required this.sectionHeaderTopMargin,
    required this.headerBottomSpacing,
    this.chordSeparator = '  ',
  });
}

class ExportService {
  /// Adaptive layout scaling profiles ordered from most spacious to most compact.
  /// The fit-to-page algorithm steps through these to achieve ONE SONG = ONE A4 PAGE
  /// while preserving comfortable readability.
  static const List<PdfLayoutProfile> layoutProfiles = [
    // Level 0: Standard spacious (Short songs e.g. Kaattu Thottappol)
    PdfLayoutProfile(
      pageMargin: 36.0,
      titleFontSize: 20.0,
      metaFontSize: 10.0,
      sectionFontSize: 11.0,
      chordFontSize: 13.0,
      chordLineSpacing: 3.5,
      sectionSpacing: 8.0,
      sectionHeaderTopMargin: 6.0,
      headerBottomSpacing: 10.0,
      chordSeparator: '  ',
    ),
    // Level 1: Medium compact (30-50 bars)
    PdfLayoutProfile(
      pageMargin: 32.0,
      titleFontSize: 18.0,
      metaFontSize: 9.5,
      sectionFontSize: 10.5,
      chordFontSize: 12.0,
      chordLineSpacing: 2.5,
      sectionSpacing: 6.0,
      sectionHeaderTopMargin: 4.0,
      headerBottomSpacing: 8.0,
      chordSeparator: '  ',
    ),
    // Level 2: High density (60-90 bars e.g. Bekhayali / Radhimaa)
    PdfLayoutProfile(
      pageMargin: 28.0,
      titleFontSize: 16.5,
      metaFontSize: 9.0,
      sectionFontSize: 10.0,
      chordFontSize: 11.0,
      chordLineSpacing: 2.0,
      sectionSpacing: 4.0,
      sectionHeaderTopMargin: 3.0,
      headerBottomSpacing: 6.0,
      chordSeparator: '  ',
    ),
    // Level 3: Extra compact (90-120 bars)
    PdfLayoutProfile(
      pageMargin: 25.0,
      titleFontSize: 15.0,
      metaFontSize: 8.5,
      sectionFontSize: 9.5,
      chordFontSize: 10.0,
      chordLineSpacing: 1.5,
      sectionSpacing: 3.0,
      sectionHeaderTopMargin: 2.0,
      headerBottomSpacing: 5.0,
      chordSeparator: '  ',
    ),
    // Level 4: Maximum single-page compression (Safe readability floor ~9 pt)
    PdfLayoutProfile(
      pageMargin: 24.0,
      titleFontSize: 14.0,
      metaFontSize: 8.0,
      sectionFontSize: 9.0,
      chordFontSize: 9.0,
      chordLineSpacing: 1.0,
      sectionSpacing: 2.0,
      sectionHeaderTopMargin: 1.5,
      headerBottomSpacing: 4.0,
      chordSeparator: ' ',
    ),
  ];

  /// Formats chords inside a single bar measure into compact lead-sheet text
  /// with slash chords intact and multiple chord changes separated by spaces.
  static String formatBarChords(
    Bar bar, {
    String emptyChar = 'N',
    String chordSeparator = '  ',
  }) {
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
    return collapsed.join(chordSeparator);
  }

  /// Groups bars in a section into lines of measures using dynamic width calculation.
  /// Prevents line overflow while maintaining intact musical measures and standard 4-bar systems.
  static List<List<String>> formatSectionLines(
    MusicalSection sec, {
    double availableWidth = 523.0,
    double chordFontSize = 13.0,
    int maxBarsPerLine = 4,
    PdfFont? font,
    String chordSeparator = '  ',
  }) {
    final List<List<String>> lines = [];
    List<String> currentLine = [];

    for (final bar in sec.bars) {
      final barStr = formatBarChords(bar, chordSeparator: chordSeparator);

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

  /// Builds a PDF Document using a specific layout profile.
  static pw.Document buildDocumentWithProfile({
    required SongAnalysis song,
    required PdfLayoutProfile profile,
    required pw.Font fontBold,
    required pw.Font fontRegular,
    required PdfFont pdfFont,
  }) {
    final pdf = pw.Document();
    final double availableWidth = 595.275 - (profile.pageMargin * 2);

    pdf.addPage(
      pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        margin: pw.EdgeInsets.all(profile.pageMargin),
        header: (context) {
          if (context.pageNumber > 1) {
            return pw.Container(
              margin: const pw.EdgeInsets.only(bottom: 8),
              padding: const pw.EdgeInsets.only(bottom: 3),
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
                      fontSize: 8.5,
                      color: PdfColors.grey800,
                    ),
                  ),
                  pw.Text(
                    'Key: ${song.key.display}  |  Tempo: ${song.tempo.bpm.toStringAsFixed(0)} BPM  |  Time: ${song.meter.display}',
                    style: pw.TextStyle(
                      font: fontRegular,
                      fontSize: 7.5,
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
          // If total pages > 1, show page numbers
          if (context.pagesCount > 1) {
            return pw.Container(
              margin: const pw.EdgeInsets.only(top: 4),
              alignment: pw.Alignment.centerRight,
              child: pw.Text(
                'Page ${context.pageNumber} of ${context.pagesCount}',
                style: pw.TextStyle(
                  font: fontRegular,
                  fontSize: 7.5,
                  color: PdfColors.grey600,
                ),
              ),
            );
          }
          return pw.SizedBox.shrink();
        },
        build: (context) {
          final List<pw.Widget> widgets = [];

          // 1. Song Title Header
          widgets.add(
            pw.Text(
              song.title,
              style: pw.TextStyle(
                font: fontBold,
                fontSize: profile.titleFontSize,
                fontWeight: pw.FontWeight.bold,
              ),
            ),
          );
          widgets.add(pw.SizedBox(height: 3));

          // 2. Compact Horizontal Metadata Line
          widgets.add(
            pw.Row(
              children: [
                pw.Text(
                  'Key: ${song.key.display}',
                  style: pw.TextStyle(font: fontBold, fontSize: profile.metaFontSize),
                ),
                pw.SizedBox(width: 20),
                pw.Text(
                  'Tempo: ${song.tempo.bpm.toStringAsFixed(0)} BPM',
                  style: pw.TextStyle(font: fontBold, fontSize: profile.metaFontSize),
                ),
                pw.SizedBox(width: 20),
                pw.Text(
                  'Time: ${song.meter.display}',
                  style: pw.TextStyle(font: fontBold, fontSize: profile.metaFontSize),
                ),
                if (song.transposeSemitones != 0) ...[
                  pw.SizedBox(width: 20),
                  pw.Text(
                    'Transposed: ${song.transposeSemitones > 0 ? "+" : ""}${song.transposeSemitones}',
                    style: pw.TextStyle(
                      font: fontBold,
                      fontSize: profile.metaFontSize,
                      color: PdfColors.indigo700,
                    ),
                  ),
                ],
              ],
            ),
          );
          widgets.add(pw.SizedBox(height: 3));
          widgets.add(pw.Divider(thickness: 0.6, color: PdfColors.grey400));
          widgets.add(pw.SizedBox(height: profile.headerBottomSpacing));

          // 3. Sections
          for (final sec in song.sections) {
            final rawName = sec.name.trim();
            final displayName = rawName.toUpperCase().endsWith(':')
                ? rawName.toUpperCase()
                : '${rawName.toUpperCase()}:';

            final lines = formatSectionLines(
              sec,
              availableWidth: availableWidth,
              chordFontSize: profile.chordFontSize,
              maxBarsPerLine: 4,
              font: pdfFont,
              chordSeparator: profile.chordSeparator,
            );

            if (lines.isEmpty) continue;

            final sectionHeaderWidget = pw.Container(
              margin: pw.EdgeInsets.only(
                top: profile.sectionHeaderTopMargin,
                bottom: 1.5,
              ),
              padding: const pw.EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              color: PdfColors.yellow100,
              child: pw.Text(
                displayName,
                style: pw.TextStyle(
                  font: fontBold,
                  fontSize: profile.sectionFontSize,
                  fontWeight: pw.FontWeight.bold,
                ),
              ),
            );

            final chordTextStyle = pw.TextStyle(
              font: fontBold,
              fontSize: profile.chordFontSize,
              lineSpacing: 1.15,
            );

            // Bind section heading + first chord line in a single non-splittable Column
            // so section heading is never orphaned at the bottom of a page
            widgets.add(
              pw.Column(
                crossAxisAlignment: pw.CrossAxisAlignment.start,
                mainAxisSize: pw.MainAxisSize.min,
                children: [
                  sectionHeaderWidget,
                  pw.SizedBox(height: profile.chordLineSpacing),
                  pw.Text('| ${lines.first.join(' | ')} |', style: chordTextStyle),
                ],
              ),
            );

            // Subsequent chord lines in the section flow naturally
            for (int i = 1; i < lines.length; i++) {
              widgets.add(pw.SizedBox(height: profile.chordLineSpacing));
              widgets.add(
                pw.Text('| ${lines[i].join(' | ')} |', style: chordTextStyle),
              );
            }

            widgets.add(pw.SizedBox(height: profile.sectionSpacing));
          }

          return widgets;
        },
      ),
    );

    return pdf;
  }

  /// Generates a musician-friendly printable chord sheet PDF matching the desktop reference lead sheet format.
  /// Implements the Fit-to-Page algorithm:
  /// - Automatically attempts to fit the complete chord sheet onto ONE A4 PAGE.
  /// - Dynamically steps through adaptive layout profiles (reducing vertical spacing, line spacing, margins, and font size in order).
  /// - Stops as soon as the complete song fits on 1 page.
  /// - For exceptionally long songs that cannot fit within safe readability limits, gracefully formats across 2 pages with running headers.
  static Future<pw.Document> generatePdfDocument(SongAnalysis song) async {
    final fontBold = pw.Font.helveticaBold();
    final fontRegular = pw.Font.helvetica();

    // Metric calculation font (accessed via a temporary dummy PdfDocument)
    final dummyPdfDoc = PdfDocument();
    final pdfFont = PdfFont.helveticaBold(dummyPdfDoc);

    pw.Document? fallbackMultiPageDoc;

    // Test adaptive layout profiles in order from most spacious (Level 0) to most compact (Level 4)
    for (final profile in layoutProfiles) {
      final candidateDoc = buildDocumentWithProfile(
        song: song,
        profile: profile,
        fontBold: fontBold,
        fontRegular: fontRegular,
        pdfFont: pdfFont,
      );

      // Measurement check: did the document fit on exactly 1 page?
      if (candidateDoc.document.pdfPageList.pages.length == 1) {
        return candidateDoc;
      }

      fallbackMultiPageDoc ??= candidateDoc;
    }

    // For exceptionally long songs that exceed 1 page even at the most compact readable profile,
    // use a comfortable readable profile (Level 2) across multiple pages.
    return fallbackMultiPageDoc ??
        buildDocumentWithProfile(
          song: song,
          profile: layoutProfiles[2],
          fontBold: fontBold,
          fontRegular: fontRegular,
          pdfFont: pdfFont,
        );
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
