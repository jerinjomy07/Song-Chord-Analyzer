import 'package:flutter/material.dart';
import '../models/chord_prediction.dart';

class ChordEditorModal extends StatefulWidget {
  final ChordPrediction chord;
  final int chordIndex;
  final Function({
    required int chordIndex,
    required String root,
    required String quality,
    String? bass,
    String? display,
  }) onSave;

  const ChordEditorModal({
    super.key,
    required this.chord,
    required this.chordIndex,
    required this.onSave,
  });

  @override
  State<ChordEditorModal> createState() => _ChordEditorModalState();
}

class _ChordEditorModalState extends State<ChordEditorModal> {
  late String _selectedRoot;
  late String _selectedQuality;
  late String _selectedBass;

  static const List<String> roots = [
    'C', 'C#', 'Db', 'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb', 'G', 'G#', 'Ab', 'A', 'A#', 'Bb', 'B', 'N'
  ];

  static const List<String> qualities = [
    'major', 'minor', '7', 'maj7', 'min7', 'dim', 'aug', 'sus4', 'sus2', '6', 'm7b5'
  ];

  @override
  void initState() {
    super.initState();
    _selectedRoot = widget.chord.root;
    _selectedQuality = widget.chord.quality;
    _selectedBass = widget.chord.bass.isNotEmpty ? widget.chord.bass : widget.chord.root;
  }

  String get _currentDisplay {
    if (_selectedRoot == 'N') return 'N';
    var disp = '$_selectedRoot$_selectedQuality';
    if (_selectedBass != _selectedRoot && _selectedBass != 'None' && _selectedBass != 'N') {
      disp += '/$_selectedBass';
    }
    return disp;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Edit Chord',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                  decoration: BoxDecoration(
                    color: Colors.indigo.shade50,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: Colors.indigo.shade200),
                  ),
                  child: Text(
                    _currentDisplay,
                    style: TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                      color: Colors.indigo.shade900,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Alternatives from ML model
            if (widget.chord.alternatives.isNotEmpty) ...[
              const Text(
                'AI Model Alternatives:',
                style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.grey),
              ),
              const SizedBox(height: 6),
              Wrap(
                spacing: 8,
                children: widget.chord.alternatives.map((alt) {
                  return ActionChip(
                    label: Text('${alt.chord} (${(alt.probability * 100).toStringAsFixed(0)}%)'),
                    onPressed: () {
                      final parts = alt.chord.split('/');
                      setState(() {
                        _selectedRoot = parts[0];
                        _selectedBass = parts.length > 1 ? parts[1] : parts[0];
                      });
                    },
                  );
                }).toList(),
              ),
              const SizedBox(height: 12),
            ],

            // Root Note Picker
            const Text('Root Note', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: roots.map((r) {
                final isSelected = _selectedRoot == r;
                return ChoiceChip(
                  label: Text(r),
                  selected: isSelected,
                  onSelected: (val) {
                    if (val) {
                      setState(() {
                        _selectedRoot = r;
                        if (_selectedBass == widget.chord.root) {
                          _selectedBass = r;
                        }
                      });
                    }
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 12),

            // Quality Picker
            const Text('Quality', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: qualities.map((q) {
                final isSelected = _selectedQuality == q;
                return ChoiceChip(
                  label: Text(q),
                  selected: isSelected,
                  onSelected: (val) {
                    if (val) setState(() => _selectedQuality = q);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 12),

            // Bass Note Picker (Inversion)
            const Text('Bass / Inversion', style: TextStyle(fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: roots.map((b) {
                final isSelected = _selectedBass == b;
                return ChoiceChip(
                  label: Text(b == _selectedRoot ? '$b (Root)' : b),
                  selected: isSelected,
                  onSelected: (val) {
                    if (val) setState(() => _selectedBass = b);
                  },
                );
              }).toList(),
            ),
            const SizedBox(height: 20),

            // Save Button
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.indigo,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              onPressed: () {
                widget.onSave(
                  chordIndex: widget.chordIndex,
                  root: _selectedRoot,
                  quality: _selectedQuality,
                  bass: _selectedBass,
                  display: _currentDisplay,
                );
                Navigator.of(context).pop();
              },
              child: const Text('Apply Chord Edit', style: TextStyle(fontSize: 16)),
            ),
          ],
        ),
      ),
    );
  }
}
