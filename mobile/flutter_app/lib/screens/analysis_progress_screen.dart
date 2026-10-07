import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import '../models/analysis_status.dart';
import '../services/analysis_engine.dart';
import '../services/history_service.dart';
import 'chord_sheet_screen.dart';

class AnalysisProgressScreen extends StatefulWidget {
  final File audioFile;
  final String songTitle;
  final AnalysisEngine analysisEngine;

  const AnalysisProgressScreen({
    super.key,
    required this.audioFile,
    required this.songTitle,
    required this.analysisEngine,
  });

  @override
  State<AnalysisProgressScreen> createState() => _AnalysisProgressScreenState();
}

class _AnalysisProgressScreenState extends State<AnalysisProgressScreen> {
  int _progress = 5;
  String _currentMessage = 'Connecting to server and initiating MIR analysis...';
  String _currentStage = 'PREPROCESSING';
  String? _errorMessage;
  Timer? _pollingTimer;
  String? _jobId;
  int _consecutivePollErrors = 0;

  static const List<Map<String, String>> pipelineStages = [
    {'id': 'PREPROCESSING', 'title': 'Audio Preprocessing & Normalization'},
    {'id': 'SEPARATING', 'title': 'Demucs Neural Stem Separation'},
    {'id': 'ANALYZING_BEATS', 'title': 'Multi-Hypothesis Beat & Tempo Tracking'},
    {'id': 'ANALYZING_KEY', 'title': 'Musical Key & Scale Detection'},
    {'id': 'ANALYZING_CHORDS', 'title': 'BTC Neural Automatic Chord Recognition'},
    {'id': 'ANALYZING_INVERSION', 'title': 'Bass Register Inversion Analysis'},
    {'id': 'ALIGNING_BARS', 'title': 'Measure Alignment & Downbeat Fusion'},
    {'id': 'DETECTING_SECTIONS', 'title': 'Section Clustering & Repetitions'},
    {'id': 'BUILDING_SHEET', 'title': 'Assembling Musician Chord Sheet'},
  ];

  @override
  void initState() {
    super.initState();
    _startAnalysis();
  }

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }

  Future<void> _startAnalysis() async {
    setState(() {
      _errorMessage = null;
      _progress = 5;
      _currentMessage = 'Uploading audio to analysis server...';
      _consecutivePollErrors = 0;
    });

    try {
      final jobId = await widget.analysisEngine.startAnalysis(
        audioFile: widget.audioFile,
        songTitle: widget.songTitle,
      );
      if (!mounted) return;
      setState(() => _jobId = jobId);

      _pollingTimer?.cancel();
      _pollingTimer = Timer.periodic(const Duration(milliseconds: 1000), (timer) async {
        try {
          final status = await widget.analysisEngine.getStatus(jobId);
          _consecutivePollErrors = 0;

          if (!mounted) return;
          setState(() {
            _progress = status.progress;
            _currentMessage = status.message.isNotEmpty ? status.message : 'Processing...';
            _currentStage = status.currentStage.isNotEmpty
                ? status.currentStage
                : status.stage.name.toUpperCase();
          });

          if (status.stage == AnalysisStage.completed) {
            timer.cancel();
            final result = await widget.analysisEngine.getResult(jobId);
            // Save to persistent SQLite History on mobile
            await HistoryService.saveAnalysis(
              analysis: result,
              sourceAudio: widget.audioFile,
            );

            if (mounted) {
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(
                  builder: (context) => ChordSheetScreen(
                    initialAnalysis: result,
                    analysisEngine: widget.analysisEngine,
                  ),
                ),
              );
            }
          } else if (status.stage == AnalysisStage.failed) {
            timer.cancel();
            if (mounted) {
              setState(() {
                _errorMessage = status.error ?? status.message;
              });
            }
          }
        } catch (pollErr) {
          _consecutivePollErrors++;
          if (_consecutivePollErrors >= 15) {
            timer.cancel();
            if (mounted) {
              setState(() {
                _errorMessage = 'Lost connection to analysis server: $pollErr';
              });
            }
          }
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _errorMessage = e.toString().replaceFirst(RegExp(r'^Exception:\s*'), '');
        });
      }
    }
  }

  int _findStageIndex(String stageId) {
    for (int i = 0; i < pipelineStages.length; i++) {
      if (stageId.contains(pipelineStages[i]['id']!)) {
        return i;
      }
    }
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    final currentStageIdx = _findStageIndex(_currentStage);

    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        title: Text(widget.songTitle),
        automaticallyImplyLeading: _errorMessage != null,
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_errorMessage != null) ...[
                  const Icon(Icons.error_outline, size: 60, color: Colors.redAccent),
                  const SizedBox(height: 16),
                  const Text(
                    'Analysis Error',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: Colors.red.shade50,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: Colors.red.shade200),
                    ),
                    child: Text(
                      _errorMessage!,
                      style: TextStyle(color: Colors.red.shade900, fontSize: 13),
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      OutlinedButton(
                        onPressed: () => Navigator.of(context).pop(),
                        child: const Text('Back to Home'),
                      ),
                      const SizedBox(width: 16),
                      ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: _startAnalysis,
                        icon: const Icon(Icons.refresh, size: 18),
                        label: const Text('Retry Analysis'),
                      ),
                    ],
                  ),
                ] else ...[
                  // Circular Progress Ring
                  Center(
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 130,
                          height: 130,
                          child: CircularProgressIndicator(
                            value: (_progress / 100.0).clamp(0.0, 1.0),
                            strokeWidth: 8,
                            backgroundColor: Colors.indigo.shade100,
                            color: Colors.indigo,
                          ),
                        ),
                        Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              '$_progress%',
                              style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                            ),
                            const Text(
                              'MIR SERVER',
                              style: TextStyle(fontSize: 9, fontWeight: FontWeight.bold, color: Colors.grey),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  Text(
                    _currentMessage,
                    style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
                    textAlign: TextAlign.center,
                  ),
                  if (_jobId != null) ...[
                    const SizedBox(height: 6),
                    Text(
                      'Session ID: ${_jobId!.length > 8 ? _jobId!.substring(0, 8) : _jobId}',
                      style: TextStyle(fontSize: 11, color: Colors.grey.shade500),
                      textAlign: TextAlign.center,
                    ),
                  ],
                  const SizedBox(height: 28),

                  // Stage list with real progression icons
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Column(
                        children: List.generate(pipelineStages.length, (idx) {
                          final stage = pipelineStages[idx];
                          final isPassed = idx < currentStageIdx;
                          final isCurrent = idx == currentStageIdx;

                          Widget leadingIcon;
                          Color textColor;
                          FontWeight textWeight;

                          if (isPassed) {
                            leadingIcon = const Icon(Icons.check_circle, size: 18, color: Colors.green);
                            textColor = Colors.grey.shade700;
                            textWeight = FontWeight.normal;
                          } else if (isCurrent) {
                            leadingIcon = const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.indigo),
                            );
                            textColor = Colors.indigo.shade900;
                            textWeight = FontWeight.bold;
                          } else {
                            leadingIcon = Icon(Icons.circle_outlined, size: 16, color: Colors.grey.shade400);
                            textColor = Colors.grey.shade500;
                            textWeight = FontWeight.normal;
                          }

                          return ListTile(
                            dense: true,
                            leading: leadingIcon,
                            title: Text(
                              stage['title']!,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: textWeight,
                                color: textColor,
                              ),
                            ),
                          );
                        }),
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
