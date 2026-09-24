import 'package:flutter/material.dart';
import '../models/bar.dart';
import '../models/chord_prediction.dart';
import 'chord_tile.dart';

class BarView extends StatelessWidget {
  final Bar bar;
  final bool isActive;
  final ChordPrediction? activeChord;
  final Function(ChordPrediction chord, int indexInSong) onChordTap;
  final List<ChordPrediction> allChords;

  const BarView({
    super.key,
    required this.bar,
    this.isActive = false,
    this.activeChord,
    required this.onChordTap,
    required this.allChords,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(minWidth: 100),
      margin: const EdgeInsets.all(4),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: isActive ? Colors.amber.shade50 : Colors.white,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isActive ? Colors.amber.shade600 : Colors.grey.shade300,
          width: isActive ? 2.0 : 1.0,
        ),
        boxShadow: [
          if (isActive)
            BoxShadow(
              color: Colors.amber.withOpacity(0.2),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Bar ${bar.barNumber}',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: isActive ? Colors.amber.shade900 : Colors.grey.shade600,
                ),
              ),
              if (bar.beats != 4)
                Text(
                  '${bar.beats}/4',
                  style: TextStyle(fontSize: 9, color: Colors.grey.shade500),
                ),
            ],
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: bar.chords.map((chord) {
              final isChordActive = activeChord != null &&
                  activeChord!.startTime == chord.startTime;
              final chordIndex = allChords.indexWhere((c) => c.startTime == chord.startTime);

              return ChordTile(
                chord: chord,
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
