import 'dart:io';
import 'package:flutter/material.dart';
import '../models/song_analysis.dart';
import '../models/chord_prediction.dart';
import '../services/analysis_engine.dart';
import '../services/audio_player_service.dart';
import '../services/history_service.dart';
import '../services/export_service.dart';
import '../widgets/bar_view.dart';
import '../widgets/chord_editor_modal.dart';
import '../widgets/audio_playback_bar.dart';

class ChordSheetScreen extends StatefulWidget {
  final SongAnalysis initialAnalysis;
  final AnalysisEngine analysisEngine;

  const ChordSheetScreen({
    super.key,
    required this.initialAnalysis,
    required this.analysisEngine,
  });

  @override
  State<ChordSheetScreen> createState() => _ChordSheetScreenState();
}

class _ChordSheetScreenState extends State<ChordSheetScreen> {
  late SongAnalysis _analysis;
  final AudioPlayerService _playerService = AudioPlayerService();
  final ScrollController _scrollController = ScrollController();
  final Map<int, GlobalKey> _barKeys = {};

  bool _autoScrollEnabled = true;
  int _activeBarNumber = -1;
  ChordPrediction? _activeChord;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _analysis = widget.initialAnalysis;
    _playerService.setActiveSong(_analysis);

    // Initialize audio source
    if (_analysis.localAudioPath != null) {
      _playerService.loadAudio(_analysis.localAudioPath!, isLocal: true);
    } else if (_analysis.audioUrl != null) {
      _playerService.loadAudio(_analysis.audioUrl!, isLocal: false);
    }

    // Listen to active bar for auto-scrolling
    _playerService.activeBarStream.listen((barNumber) {
      if (mounted) {
        setState(() => _activeBarNumber = barNumber);
        if (_autoScrollEnabled) {
          _scrollToBar(barNumber);
        }
      }
    });

    // Listen to active chord
    _playerService.activeChordStream.listen((chord) {
      if (mounted) {
        setState(() => _activeChord = chord);
      }
    });
  }

  @override
  void dispose() {
    _playerService.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBar(int barNumber) {
    final key = _barKeys[barNumber];
    if (key != null && key.currentContext != null) {
      Scrollable.ensureVisible(
        key.currentContext!,
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
        alignment: 0.3,
      );
    }
  }

  Future<void> _handleTranspose(int semitones) async {
    if (_isSaving || semitones == 0) return;
    setState(() => _isSaving = true);
    try {
      final previousAudioPath = _analysis.localAudioPath;
      final updated = await widget.analysisEngine.transpose(
        currentAnalysis: _analysis,
        semitones: semitones,
      );
      if (updated.localAudioPath == null || updated.localAudioPath!.isEmpty) {
        updated.localAudioPath = previousAudioPath;
      }
      setState(() {
        _analysis = updated;
        _playerService.setActiveSong(_analysis);
        _isSaving = false;
      });
      // Save changes to SQLite
      await HistoryService.saveAnalysis(
        analysis: _analysis,
        sourceAudio: _analysis.localAudioPath != null ? File(_analysis.localAudioPath!) : null,
      );
    } catch (e) {
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Transposition failed: $e')),
      );
    }
  }

  void _showMeterDialog() {
    final meters = [
      {'display': '4/4', 'num': 4, 'den': 4, 'sub': 'Common Time (Standard)'},
      {'display': '3/4', 'num': 3, 'den': 4, 'sub': 'Waltz / Triple Meter'},
      {'display': '7/8', 'num': 7, 'den': 8, 'sub': 'Asymmetric 7/8 (2+3+2 or 3+2+2)'},
      {'display': '6/8', 'num': 6, 'den': 8, 'sub': 'Compound Duple (6/8)'},
      {'display': '2/4', 'num': 2, 'den': 4, 'sub': 'Duple Meter (March)'},
      {'display': '12/8', 'num': 12, 'den': 8, 'sub': 'Compound Quadruple (Blues / Ballad)'},
    ];

    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(16),
              child: Text(
                'Change Time Signature',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.bold),
              ),
            ),
            const Divider(height: 1),
            ...meters.map((m) {
              final isCurrent = _analysis.meter.display == m['display'];
              return ListTile(
                leading: Container(
                  width: 44,
                  alignment: Alignment.center,
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  decoration: BoxDecoration(
                    color: isCurrent ? Colors.indigoAccent : Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    m['display'] as String,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: isCurrent ? Colors.white : Colors.black87,
                    ),
                  ),
                ),
                title: Text(m['display'] as String),
                subtitle: Text(m['sub'] as String),
                trailing: isCurrent ? const Icon(Icons.check, color: Colors.indigoAccent) : null,
                onTap: () async {
                  Navigator.of(context).pop();
                  if (!isCurrent) {
                    await _handleMeterChange(
                      numerator: m['num'] as int,
                      denominator: m['den'] as int,
                    );
                  }
                },
              );
            }),
          ],
        ),
      ),
    );
  }

  Future<void> _handleMeterChange({
    required int numerator,
    required int denominator,
    String? subgrouping,
  }) async {
    setState(() => _isSaving = true);
    try {
      final previousAudioPath = _analysis.localAudioPath;
      final updated = await widget.analysisEngine.changeMeter(
        currentAnalysis: _analysis,
        numerator: numerator,
        denominator: denominator,
        subgrouping: subgrouping,
      );
      if (updated.localAudioPath == null || updated.localAudioPath!.isEmpty) {
        updated.localAudioPath = previousAudioPath;
      }
      setState(() {
        _analysis = updated;
        _playerService.setActiveSong(_analysis);
        _isSaving = false;
      });
      // Save changes to SQLite
      await HistoryService.saveAnalysis(
        analysis: _analysis,
        sourceAudio: _analysis.localAudioPath != null ? File(_analysis.localAudioPath!) : null,
      );
    } catch (e) {
      setState(() => _isSaving = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Time signature update failed: $e')),
      );
    }
  }


  void _openChordEditor(ChordPrediction chord, int indexInSong) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (context) => ChordEditorModal(
        chord: chord,
        chordIndex: indexInSong,
        onSave: ({
          required int chordIndex,
          required String root,
          required String quality,
          String? bass,
          String? display,
        }) async {
          final originalChord = chord.display;
          final previousAudioPath = _analysis.localAudioPath;
          final updated = await widget.analysisEngine.editChord(
            currentAnalysis: _analysis,
            chordIndex: chordIndex,
            root: root,
            quality: quality,
            bass: bass,
            display: display,
          );
          if (updated.localAudioPath == null || updated.localAudioPath!.isEmpty) {
            updated.localAudioPath = previousAudioPath;
          }
          setState(() {
            _analysis = updated;
            _playerService.setActiveSong(_analysis);
          });

          // Record ML correction and persist
          await HistoryService.recordCorrection(
            songId: _analysis.id,
            chordIndex: chordIndex,
            originalChord: originalChord,
            correctedChord: display ?? '$root$quality',
            bar: chord.barPosition,
            beat: chord.beat,
            confidence: chord.confidence,
          );

          if (_analysis.localAudioPath != null) {
            await HistoryService.saveAnalysis(
              analysis: _analysis,
              sourceAudio: File(_analysis.localAudioPath!),
            );
          }
        },
      ),
    );
  }

  void _renameTitle() {
    final controller = TextEditingController(text: _analysis.title);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Rename Song Title'),
        content: TextField(
          controller: controller,
          autofocus: true,
          decoration: const InputDecoration(labelText: 'Title'),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final newTitle = controller.text.trim();
              if (newTitle.isNotEmpty) {
                setState(() => _analysis.title = newTitle);
                await HistoryService.updateSongTitle(_analysis.id, newTitle);
                Navigator.of(context).pop();
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  void _showExportMenu() {
    showModalBottomSheet(
      context: context,
      builder: (context) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.picture_as_pdf, color: Colors.red),
              title: const Text('Export Printable PDF Chart'),
              subtitle: const Text('Standard sheet music layout with boxed bars'),
              onTap: () {
                Navigator.of(context).pop();
                ExportService.exportPdf(_analysis);
              },
            ),
            ListTile(
              leading: const Icon(Icons.text_snippet, color: Colors.blue),
              title: const Text('Export Monospace TXT Chart'),
              subtitle: const Text('Plain ASCII text for stage binders'),
              onTap: () {
                Navigator.of(context).pop();
                ExportService.exportTxt(_analysis);
              },
            ),
            ListTile(
              leading: const Icon(Icons.code, color: Colors.green),
              title: const Text('Export JSON Analysis'),
              subtitle: const Text('Complete structured music data contract'),
              onTap: () {
                Navigator.of(context).pop();
                ExportService.exportJson(_analysis);
              },
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade100,
      appBar: AppBar(
        title: GestureDetector(
          onTap: _renameTitle,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(
                child: Text(
                  _analysis.title,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: 4),
              const Icon(Icons.edit, size: 14, color: Colors.indigoAccent),
            ],
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.share),
            tooltip: 'Export Chart',
            onPressed: _showExportMenu,
          ),
        ],
      ),
      body: Column(
        children: [
          if (_isSaving) const LinearProgressIndicator(),
          // Metadata & Transpose Header Bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: Colors.white,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Key, BPM, Meter badges
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.indigo.shade50,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        _analysis.key.display,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Colors.indigo.shade900,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.grey.shade100,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${_analysis.tempo.bpm.toStringAsFixed(0)} BPM',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                      ),
                    ),
                    const SizedBox(width: 6),
                    InkWell(
                      borderRadius: BorderRadius.circular(6),
                      onTap: _isSaving ? null : _showMeterDialog,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.grey.shade100,
                          borderRadius: BorderRadius.circular(6),
                          border: Border.all(color: Colors.grey.shade300),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              _analysis.meter.display,
                              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                            ),
                            const SizedBox(width: 2),
                            const Icon(Icons.arrow_drop_down, size: 14, color: Colors.grey),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),

                // Transpose Controls
                Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.remove, size: 18),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      tooltip: 'Transpose Down',
                      onPressed: _isSaving ? null : () => _handleTranspose(-1),
                    ),
                    InkWell(
                      borderRadius: BorderRadius.circular(4),
                      onTap: (_isSaving || _analysis.transposeSemitones == 0)
                          ? null
                          : () => _handleTranspose(-_analysis.transposeSemitones),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                        child: Text(
                          _analysis.transposeSemitones == 0
                              ? 'Key'
                              : '${_analysis.transposeSemitones > 0 ? "+" : ""}${_analysis.transposeSemitones}',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: _analysis.transposeSemitones != 0
                                ? Colors.indigoAccent
                                : Colors.grey.shade800,
                          ),
                        ),
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.add, size: 18),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                      tooltip: 'Transpose Up',
                      onPressed: _isSaving ? null : () => _handleTranspose(1),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const Divider(height: 1),

          // Chord Sheet Scrollable Body
          Expanded(
            child: ListView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
              itemCount: _analysis.sections.length,
              itemBuilder: (context, secIndex) {
                final section = _analysis.sections[secIndex];

                return Container(
                  margin: const EdgeInsets.only(bottom: 20),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Section Header Pill
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.indigo.shade600,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          section.name,
                          style: const TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(height: 8),

                      // Section Bars Grid
                      Wrap(
                        spacing: 4,
                        runSpacing: 6,
                        children: section.bars.map((bar) {
                          final barKey = _barKeys.putIfAbsent(
                            bar.barNumber,
                            () => GlobalKey(),
                          );

                          return KeyedSubtree(
                            key: barKey,
                            child: BarView(
                              bar: bar,
                              isActive: bar.barNumber == _activeBarNumber,
                              activeChord: _activeChord,
                              allChords: _analysis.chords,
                              onChordTap: (chord, indexInSong) {
                                _openChordEditor(chord, indexInSong);
                              },
                            ),
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                );
              },
            ),
          ),

          // Bottom Playback Bar
          AudioPlaybackBar(
            playerService: _playerService,
            autoScrollEnabled: _autoScrollEnabled,
            onAutoScrollChanged: (val) {
              setState(() => _autoScrollEnabled = val);
            },
          ),
        ],
      ),
    );
  }
}
