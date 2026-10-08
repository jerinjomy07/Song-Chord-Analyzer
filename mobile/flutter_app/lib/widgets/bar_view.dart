import 'package:flutter/material.dart';
import '../models/bar.dart';
import '../models/chord_prediction.dart';
import 'chord_tile.dart';

class BarView extends StatelessWidget {
  final Bar bar;
  final String songMeter;
  final bool isCompact;
  final bool isActive;
  final ChordPrediction? activeChord;
  final Function(ChordPrediction chord, int indexInSong) onChordTap;
  final List<ChordPrediction> allChords;

  const BarView({
    super.key,
    required this.bar,
    this.songMeter = '4/4',
    this.isCompact = true,
    this.isActive = false,
    this.activeChord,
    required this.onChordTap,
    required this.allChords,
  });

  @override
  Widget build(BuildContext context) {
    final meterText = bar.timeSignature.isNotEmpty
        ? bar.timeSignature
        : (songMeter.isNotEmpty ? songMeter : '${bar.beats}/4');

    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      padding: EdgeInsets.symmetric(
        horizontal: isCompact ? 6 : 8,
        vertical: isCompact ? 5 : 7,
      ),
      decoration: BoxDecoration(
        color: isActive ? Colors.amber.shade50 : Colors.white,
        borderRadius: BorderRadius.circular(isCompact ? 6 : 8),
        border: Border.all(
          color: isActive ? Colors.amber.shade600 : Colors.grey.shade300,
          width: isActive ? 1.5 : 1.0,
        ),
        boxShadow: [
          if (isActive)
            BoxShadow(
              color: Colors.amber.withValues(alpha: 0.25),
              blurRadius: 4,
              offset: const Offset(0, 1),
            )
          else
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.02),
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Bar Number & Meter Indicator
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Bar ${bar.barNumber}',
                style: TextStyle(
                  fontSize: isCompact ? 10 : 11,
                  fontWeight: FontWeight.bold,
                  color: isActive ? Colors.amber.shade900 : Colors.grey.shade600,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: isActive ? Colors.amber.shade100 : Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(
                  meterText,
                  style: TextStyle(
                    fontSize: isCompact ? 9 : 10,
                    fontWeight: FontWeight.w600,
                    color: isActive ? Colors.amber.shade900 : Colors.grey.shade700,
                  ),
                ),
              ),
            ],
          ),
          SizedBox(height: isCompact ? 4 : 6),
          // Chord Chips Wrap
          if (bar.chords.isEmpty)
            ChordTile(
              chord: ChordPrediction(
                root: 'N',
                quality: '',
                bass: '',
                display: 'N',
                startTime: bar.startTime,
                endTime: bar.endTime,
                duration: (bar.endTime > bar.startTime) ? (bar.endTime - bar.startTime) : 1.0,
                confidence: 1.0,
                beat: 1,
                barPosition: bar.barNumber,
              ),
              isCompact: isCompact,
              isActive: isActive,
              onTap: () {},
            )
          else
            Wrap(
              spacing: isCompact ? 4 : 6,
              runSpacing: isCompact ? 4 : 5,
              children: bar.chords.map((chord) {
                final isChordActive = activeChord != null &&
                    activeChord!.startTime == chord.startTime;
                final chordIndex = allChords.indexWhere((c) => c.startTime == chord.startTime);

                return ChordTile(
                  chord: chord,
                  isCompact: isCompact,
                  isActive: isChordActive,
                  onTap: () => onChordTap(chord, chordIndex >= 0 ? chordIndex : 0),
                );
              }).toList(),
            ),
        ],
      ),
    );
  }
}
