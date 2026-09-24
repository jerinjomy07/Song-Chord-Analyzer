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
  String _currentMessage = 'Initiating analysis...';
  String _currentStage = 'PREPROCESSING';
  String? _errorMessage;
  Timer? _pollingTimer;
  String? _jobId;

  static const List<Map<String, String>> pipelineStages = [
    {'id': 'PREPROCESSING', 'title': 'Loading & Preprocessing Audio'},
    {'id': 'SEPARATING', 'title': 'Demucs Stem Separation'},
    {'id': 'ANALYZING_BEATS', 'title': 'Detecting Beats & Tempo'},
    {'id': 'ANALYZING_KEY', 'title': 'Detecting Musical Key'},
    {'id': 'ANALYZING_CHORDS', 'title': 'BTC Neural Chord Recognition'},
    {'id': 'ANALYZING_INVERSION', 'title': 'Sub-Bass Inversion Tracking'},
    {'id': 'ALIGNING_BARS', 'title': 'Aligning Bars & Downbeats'},
    {'id': 'BUILDING_SHEET', 'title': 'Generating Musician Chord Sheet'},
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
    try {
      final jobId = await widget.analysisEngine.startAnalysis(
        audioFile: widget.audioFile,
        songTitle: widget.songTitle,
      );
      setState(() => _jobId = jobId);

      _pollingTimer = Timer.periodic(const Duration(milliseconds: 1500), (timer) async {
        try {
          final status = await widget.analysisEngine.getStatus(jobId);
          setState(() {
            _progress = status.progress;
            _currentMessage = status.message;
            _currentStage = status.stage.name.toUpperCase();
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
            setState(() {
              _errorMessage = status.error ?? status.message;
            });
          }
        } catch (pollErr) {
          // Keep polling or report if fatal
        }
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
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
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_errorMessage != null) ...[
                  const Icon(Icons.error_outline, size: 56, color: Colors.red),
                  const SizedBox(height: 16),
                  const Text(
                    'Analysis Error',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _errorMessage!,
                    style: TextStyle(color: Colors.red.shade700, fontSize: 13),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: const Text('Back to Home'),
                  ),
                ] else ...[
                  // Circular Progress Ring
                  Center(
                    child: Stack(
                      alignment: Alignment.center,
                      children: [
                        SizedBox(
                          width: 120,
                          height: 120,
                          child: CircularProgressIndicator(
                            value: _progress / 100.0,
                            strokeWidth: 8,
                            backgroundColor: Colors.indigo.shade100,
                            color: Colors.indigo,
                          ),
                        ),
                        Text(
                          '$_progress%',
                          style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),

                  Text(
                    _currentMessage,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 32),

                  // Stage list
                  Card(
                    elevation: 1,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Column(
                        children: pipelineStages.map((stage) {
                          final isCurrent = _currentStage.contains(stage['id']!);
                          return ListTile(
                            dense: true,
                            leading: Icon(
                              isCurrent ? Icons.sync : Icons.circle_outlined,
                              size: 16,
                              color: isCurrent ? Colors.indigo : Colors.grey.shade400,
                            ),
                            title: Text(
                              stage['title']!,
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: isCurrent ? FontWeight.bold : FontWeight.normal,
                                color: isCurrent ? Colors.indigo.shade900 : Colors.grey.shade700,
                              ),
                            ),
                          );
                        }).toList(),
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
