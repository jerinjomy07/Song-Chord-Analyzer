import 'dart:io';
import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import '../models/history_song.dart';
import '../services/history_service.dart';
import '../services/analysis_engine.dart';
import 'analysis_progress_screen.dart';
import 'chord_sheet_screen.dart';
import 'history_screen.dart';
import 'settings_screen.dart';

class HomeScreen extends StatefulWidget {
  final AnalysisEngine analysisEngine;

  const HomeScreen({
    super.key,
    required this.analysisEngine,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  File? _selectedAudioFile;
  String _songTitle = '';
  List<HistorySong> _recentSongs = [];
  bool _isLoadingHistory = false;

  @override
  void initState() {
    super.initState();
    _loadRecentSongs();
  }

  Future<void> _loadRecentSongs() async {
    setState(() => _isLoadingHistory = true);
    try {
      final songs = await HistoryService.getSongs(sortBy: 'last_opened_at', ascending: false);
      setState(() {
        _recentSongs = songs.take(5).toList();
        _isLoadingHistory = false;
      });
    } catch (_) {
      setState(() => _isLoadingHistory = false);
    }
  }

  Future<void> _pickAudioFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg'],
    );

    if (result != null && result.files.single.path != null) {
      final file = File(result.files.single.path!);
      final filename = result.files.single.name;
      final cleanTitle = filename.replaceAll(RegExp(r'\.[a-zA-Z0-9]+$'), '').replaceAll('_', ' ');

      setState(() {
        _selectedAudioFile = file;
        _songTitle = cleanTitle;
      });
    }
  }

  void _startAnalysis() {
    if (_selectedAudioFile == null) return;

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => AnalysisProgressScreen(
          audioFile: _selectedAudioFile!,
          songTitle: _songTitle.trim().isEmpty ? 'Untitled Song' : _songTitle.trim(),
          analysisEngine: widget.analysisEngine,
        ),
      ),
    ).then((_) => _loadRecentSongs());
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        title: Row(
          children: const [
            Icon(Icons.music_note, color: Colors.indigo),
            SizedBox(width: 8),
            Text(
              'Song Chord Analyzer',
              style: TextStyle(fontWeight: FontWeight.bold, fontSize: 18),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: 'Song Library / History',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (context) => HistoryScreen(
                    analysisEngine: widget.analysisEngine,
                  ),
                ),
              ).then((_) => _loadRecentSongs());
            },
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            tooltip: 'Settings',
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Hero Card: Upload Audio
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: Column(
                  children: [
                    CircleAvatar(
                      radius: 36,
                      backgroundColor: Colors.indigo.shade50,
                      child: Icon(Icons.audio_file, size: 40, color: Colors.indigo.shade600),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Automated Music Chord Analysis',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Select any MP3, WAV, FLAC, or M4A file to extract chords, key, BPM, and section charts.',
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 20),

                    // Pick File Button
                    ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.indigo,
                        foregroundColor: Colors.white,
                        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                      ),
                      onPressed: _pickAudioFile,
                      icon: const Icon(Icons.folder_open),
                      label: Text(_selectedAudioFile == null ? 'Select Audio File' : 'Change Audio File'),
                    ),

                    if (_selectedAudioFile != null) ...[
                      const SizedBox(height: 16),
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.indigo.shade50.withOpacity(0.5),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.indigo.shade100),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            TextFormField(
                              initialValue: _songTitle,
                              decoration: const InputDecoration(
                                labelText: 'Song Title',
                                border: OutlineInputBorder(),
                                isDense: true,
                              ),
                              onChanged: (val) => _songTitle = val,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'File: ${_selectedAudioFile!.path.split(Platform.pathSeparator).last}',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.amber.shade700,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                        ),
                        onPressed: _startAnalysis,
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.auto_awesome),
                            SizedBox(width: 8),
                            Text('ANALYZE SONG', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                          ],
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 24),

            // Recent Songs Section
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Recent Songs',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                TextButton(
                  onPressed: () {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (context) => HistoryScreen(
                          analysisEngine: widget.analysisEngine,
                        ),
                      ),
                    ).then((_) => _loadRecentSongs());
                  },
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 8),

            if (_isLoadingHistory)
              const Center(child: CircularProgressIndicator())
            else if (_recentSongs.isEmpty)
              Container(
                padding: const EdgeInsets.all(24),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.grey.shade200),
                ),
                child: Center(
                  child: Text(
                    'No analyzed songs yet. Select an audio file above to begin!',
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
                    textAlign: TextAlign.center,
                  ),
                ),
              )
            else
              ListView.builder(
                shrinkWrap: true,
                physics: const NeverScrollableScrollPhysics(),
                itemCount: _recentSongs.length,
                itemBuilder: (context, index) {
                  final song = _recentSongs[index];
                  return Card(
                    elevation: 1,
                    margin: const EdgeInsets.only(bottom: 8),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    child: ListTile(
                      leading: CircleAvatar(
                        backgroundColor: Colors.indigo.shade100,
                        child: Text(
                          song.keyDisplay.split(' ').first,
                          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.indigo.shade900),
                        ),
                      ),
                      title: Text(
                        song.title,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      subtitle: Text(
                        '${song.keyDisplay} • ${song.bpm.toStringAsFixed(0)} BPM • ${song.timeSignature}',
                        style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () async {
                        final analysis = await HistoryService.loadAnalysis(song.id);
                        if (analysis != null && mounted) {
                          Navigator.of(context).push(
                            MaterialPageRoute(
                              builder: (context) => ChordSheetScreen(
                                initialAnalysis: analysis,
                                analysisEngine: widget.analysisEngine,
                              ),
                            ),
                          ).then((_) => _loadRecentSongs());
                        }
                      },
                    ),
                  );
                },
              ),
          ],
        ),
      ),
    );
  }
}
