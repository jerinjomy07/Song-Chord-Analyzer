import 'package:flutter/material.dart';
import '../models/chord_prediction.dart';

class ChordTile extends StatelessWidget {
  final ChordPrediction chord;
  final bool isActive;
  final bool isCompact;
  final VoidCallback onTap;

  const ChordTile({
    super.key,
    required this.chord,
    this.isActive = false,
    this.isCompact = true,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final isLowConfidence = chord.confidence < 0.65;
    final chordText = chord.display.isEmpty ? 'N' : chord.display;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        constraints: BoxConstraints(
          minWidth: isCompact ? 36 : 44,
          minHeight: isCompact ? 28 : 34,
        ),
        padding: EdgeInsets.symmetric(
          horizontal: isCompact ? 6 : 8,
          vertical: isCompact ? 4 : 6,
        ),
        decoration: BoxDecoration(
          color: isActive
              ? Colors.amber.shade100
              : (isLowConfidence ? Colors.red.shade50 : Colors.indigo.shade50),
          border: Border.all(
            color: isActive
                ? Colors.amber.shade700
                : (isLowConfidence ? Colors.red.shade300 : Colors.indigo.shade200),
            width: isActive ? 1.5 : 1.0,
          ),
          borderRadius: BorderRadius.circular(5),
          boxShadow: [
            if (isActive)
              BoxShadow(
                color: Colors.amber.withValues(alpha: 0.3),
                blurRadius: 4,
                offset: const Offset(0, 1),
              ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(
                chordText,
                style: TextStyle(
                  fontSize: isCompact ? 13 : 15,
                  fontWeight: FontWeight.bold,
                  letterSpacing: -0.2,
                  color: isActive
                      ? Colors.amber.shade900
                      : (isLowConfidence ? Colors.red.shade900 : Colors.indigo.shade900),
                ),
              ),
            ),
            if (isLowConfidence)
              Padding(
                padding: const EdgeInsets.only(top: 1),
                child: Text(
                  '?',
                  style: TextStyle(
                    fontSize: isCompact ? 8 : 9,
                    color: Colors.red.shade700,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
