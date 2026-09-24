import 'package:flutter/material.dart';
import '../models/chord_prediction.dart';

class ChordTile extends StatelessWidget {
  final ChordPrediction chord;
  final bool isActive;
  final VoidCallback onTap;

  const ChordTile({
    super.key,
    required this.chord,
    this.isActive = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isLowConfidence = chord.confidence < 0.65;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: isActive
              ? Colors.amber.shade100
              : (isLowConfidence ? Colors.red.shade50 : Colors.indigo.shade50),
          border: Border.all(
            color: isActive
                ? Colors.amber.shade700
                : (isLowConfidence ? Colors.red.shade300 : Colors.indigo.shade200),
            width: isActive ? 2.0 : 1.0,
          ),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Text(
              chord.display.isEmpty ? 'N' : chord.display,
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: isActive
                    ? Colors.amber.shade900
                    : (isLowConfidence ? Colors.red.shade900 : Colors.indigo.shade900),
              ),
            ),
            if (isLowConfidence)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text(
                  '?',
                  style: TextStyle(fontSize: 10, color: Colors.red.shade700, fontWeight: FontWeight.bold),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
