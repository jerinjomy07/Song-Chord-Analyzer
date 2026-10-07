import '../models/song_analysis.dart';
import '../models/chord_prediction.dart';
import '../models/bar.dart';
import '../models/musical_section.dart';

class TransposeService {
  static const List<String> chromaticSharps = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
  ];

  static const List<String> chromaticFlats = [
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
  ];

  static const Map<String, String> enharmonicSharpToFlat = {
    'C#': 'Db',
    'D#': 'Eb',
    'F#': 'Gb',
    'G#': 'Ab',
    'A#': 'Bb',
  };

  static const Map<String, String> enharmonicFlatToSharp = {
    'Db': 'C#',
    'Eb': 'D#',
    'Gb': 'F#',
    'Ab': 'G#',
    'Bb': 'A#',
  };

  static const Map<String, int> pitchToSemitone = {
    'C': 0, 'B#': 0,
    'C#': 1, 'Db': 1,
    'D': 2,
    'D#': 3, 'Eb': 3,
    'E': 4, 'Fb': 4,
    'F': 5, 'E#': 5,
    'F#': 6, 'Gb': 6,
    'G': 7,
    'G#': 8, 'Ab': 8,
    'A': 9,
    'A#': 10, 'Bb': 10,
    'B': 11, 'Cb': 11,
  };

  static const List<String> flatKeys = [
    'F', 'Bb', 'Eb', 'Ab', 'Db', 'Gb', 'Dm', 'Gm', 'Cm', 'Fm', 'Bbm'
  ];

  static const Map<String, String> qualityDisplayMap = {
    'maj': '',
    'major': '',
    'min': 'm',
    'minor': 'm',
    'dim': 'dim',
    'aug': 'aug',
    '7': '7',
    'maj7': 'maj7',
    'min7': 'm7',
    'dim7': 'dim7',
    'hdim7': 'm7b5',
    'sus2': 'sus2',
    'sus4': 'sus4',
    'none': '',
  };

  static int normalizeTransposeSemitones(int totalSemitones) {
    final mod = totalSemitones % 12;
    if (totalSemitones < 0 && mod != 0) {
      return mod - 12;
    }
    return mod;
  }

  static String transposePitch(String pitch, int semitones, {bool preferFlats = false}) {
    final clean = pitch.trim();
    if (clean == 'N' || clean == 'X' || clean.isEmpty) return clean;

    final normalized = enharmonicFlatToSharp[clean] ?? clean;
    final currSemi = pitchToSemitone[normalized] ?? 0;
    final newSemi = (currSemi + semitones) % 12;
    final nonNegative = (newSemi + 12) % 12;

    var transposed = chromaticSharps[nonNegative];
    if (preferFlats && enharmonicSharpToFlat.containsKey(transposed)) {
      transposed = enharmonicSharpToFlat[transposed]!;
    }

    return transposed;
  }

  static ChordPrediction transposeChord(ChordPrediction chord, int semitones, {bool preferFlats = false}) {
    if (chord.root == 'N' || chord.root == 'X' || semitones == 0) {
      return chord;
    }

    final newRoot = transposePitch(chord.root, semitones, preferFlats: preferFlats);
    final newBass = chord.bass.isNotEmpty && chord.bass != chord.root
        ? transposePitch(chord.bass, semitones, preferFlats: preferFlats)
        : newRoot;

    final qualDisplay = qualityDisplayMap[chord.quality.toLowerCase()] ?? chord.quality;
    var newDisplay = '$newRoot$qualDisplay';
    if (newBass != newRoot) {
      newDisplay += '/$newBass';
    }

    final newAlternatives = chord.alternatives.map((alt) {
      return ChordCandidate(
        chord: alt.chord,
        probability: alt.probability,
      );
    }).toList();

    return ChordPrediction(
      root: newRoot,
      quality: chord.quality,
      bass: newBass,
      inversion: chord.inversion,
      display: newDisplay,
      startTime: chord.startTime,
      endTime: chord.endTime,
      duration: chord.duration,
      beatPosition: chord.beatPosition,
      barPosition: chord.barPosition,
      beat: chord.beat,
      beatDuration: chord.beatDuration,
      confidence: chord.confidence,
      needsReview: chord.needsReview,
      alternatives: newAlternatives,
    );
  }

  static SongAnalysis transposeSong(SongAnalysis analysis, int semitones) {
    if (semitones == 0) return analysis;

    // Determine if target key is a flat key
    final targetTonicInitial = transposePitch(analysis.key.tonic, semitones, preferFlats: false);
    final isMinor = analysis.key.mode.toLowerCase() == 'minor';
    final testKeyStr = '$targetTonicInitial${isMinor ? "m" : ""}';
    final preferFlats = flatKeys.contains(testKeyStr);
    final targetTonic = transposePitch(analysis.key.tonic, semitones, preferFlats: preferFlats);

    final modeName = analysis.key.mode.isNotEmpty
        ? '${analysis.key.mode[0].toUpperCase()}${analysis.key.mode.substring(1)}'
        : 'Major';
    final newKeyDisplay = '$targetTonic $modeName';

    final newKey = KeyAnalysis(
      tonic: targetTonic,
      mode: analysis.key.mode,
      display: newKeyDisplay,
      confidence: analysis.key.confidence,
    );

    final newChords = analysis.chords
        .map((c) => transposeChord(c, semitones, preferFlats: preferFlats))
        .toList();

    final newSections = analysis.sections.map((sec) {
      final newBars = sec.bars.map((bar) {
        final newBarChords = bar.chords
            .map((c) => transposeChord(c, semitones, preferFlats: preferFlats))
            .toList();
        final newBarDisplay = newBarChords.map((c) => c.display).join(' | ');

        return Bar(
          barNumber: bar.barNumber,
          startTime: bar.startTime,
          endTime: bar.endTime,
          beats: bar.beats,
          timeSignature: bar.timeSignature,
          display: newBarDisplay,
          chords: newBarChords,
        );
      }).toList();

      return MusicalSection(
        sectionId: sec.sectionId,
        name: sec.name,
        startTime: sec.startTime,
        endTime: sec.endTime,
        startBar: sec.startBar,
        endBar: sec.endBar,
        bars: newBars,
        isRepeated: sec.isRepeated,
        repeatOfSectionId: sec.repeatOfSectionId,
      );
    }).toList();

    final cumulativeTranspose = normalizeTransposeSemitones(analysis.transposeSemitones + semitones);

    return SongAnalysis(
      schemaVersion: analysis.schemaVersion,
      id: analysis.id,
      title: analysis.title,
      metadata: analysis.metadata,
      pipelineMetadata: analysis.pipelineMetadata,
      key: newKey,
      tempo: analysis.tempo,
      meter: analysis.meter,
      beatGrid: analysis.beatGrid,
      sections: newSections,
      chords: newChords,
      transposeSemitones: cumulativeTranspose,
      audioUrl: analysis.audioUrl,
      localAudioPath: analysis.localAudioPath,
      hasStems: analysis.hasStems,
      sourceMetadata: analysis.sourceMetadata,
      rawPredictions: analysis.rawPredictions,
      debugView: analysis.debugView,
    );
  }
}
