import '../models/song_analysis.dart';
import '../models/chord_prediction.dart';

class TransposeService {
  static const List<String> chromaticSharps = [
    'C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'
  ];

  static const List<String> chromaticFlats = [
    'C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'
  ];

  static const Map<String, int> noteToPitch = {
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

  static String transposePitch(String pitch, int semitones, {bool preferFlats = false}) {
    final clean = pitch.trim();
    if (clean == 'N' || clean.isEmpty) return clean;

    final base = noteToPitch[clean];
    if (base == null) return clean;

    final newPitchClass = ((base + semitones) % 12 + 12) % 12;
    return preferFlats ? chromaticFlats[newPitchClass] : chromaticSharps[newPitchClass];
  }

  static ChordPrediction transposeChord(ChordPrediction chord, int semitones, {bool preferFlats = false}) {
    if (chord.root == 'N') return chord;

    final newRoot = transposePitch(chord.root, semitones, preferFlats: preferFlats);
    final newBass = chord.bass.isNotEmpty && chord.bass != chord.root
        ? transposePitch(chord.bass, semitones, preferFlats: preferFlats)
        : newRoot;

    var newDisplay = '$newRoot${chord.quality}';
    if (newBass != newRoot) {
      newDisplay += '/$newBass';
    }

    final newAlternatives = chord.alternatives.map((alt) {
      // Basic transposing of alternatives
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
      beat: chord.beat,
      beatDuration: chord.beatDuration,
      confidence: chord.confidence,
      needsReview: chord.needsReview,
      alternatives: newAlternatives,
    );
  }

  static SongAnalysis transposeSong(SongAnalysis analysis, int semitones) {
    if (semitones == 0) return analysis;

    final bool preferFlats = analysis.key.tonic.contains('b') ||
        ['F', 'Bb', 'Eb', 'Ab', 'Db'].contains(analysis.key.tonic);

    final newKeyTonic = transposePitch(analysis.key.tonic, semitones, preferFlats: preferFlats);
    final newKeyDisplay = '$newKeyTonic ${analysis.key.mode.substring(0, 1).toUpperCase()}${analysis.key.mode.substring(1)}';

    final newKey = KeyAnalysis(
      tonic: newKeyTonic,
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

    return SongAnalysis(
      id: analysis.id,
      title: analysis.title,
      metadata: analysis.metadata,
      key: newKey,
      tempo: analysis.tempo,
      meter: analysis.meter,
      beatGrid: analysis.beatGrid,
      sections: newSections,
      chords: newChords,
      transposeSemitones: semitones,
      audioUrl: analysis.audioUrl,
      localAudioPath: analysis.localAudioPath,
    );
  }
}
