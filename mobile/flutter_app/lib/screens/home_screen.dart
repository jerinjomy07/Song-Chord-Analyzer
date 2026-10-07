import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';
import '../models/history_song.dart';
import '../services/history_service.dart';
import '../services/analysis_engine.dart';
import '../services/youtube_downloader_service.dart';
import '../models/server_config.dart';
import '../services/server_config_service.dart';
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
  // Input source: 'file' or 'youtube'
  String _inputMode = 'file';

  // File Picker State
  File? _selectedAudioFile;
  String _songTitle = '';

  // YouTube State
  final TextEditingController _ytUrlController = TextEditingController();
  YouTubeVideoMeta? _ytMeta;
  bool _isFetchingYtInfo = false;
  String? _ytError;
  bool _isDownloadingYtAudio = false;
  double _ytDownloadProgress = 0.0;
  String _ytDownloadStatus = '';

  // History State
  List<HistorySong> _recentSongs = [];
  bool _isLoadingHistory = false;

  @override
  void initState() {
    super.initState();
    _loadRecentSongs();
  }

  @override
  void dispose() {
    _ytUrlController.dispose();
    super.dispose();
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

  void _startAnalysisWithFile(File file, String title) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => AnalysisProgressScreen(
          audioFile: file,
          songTitle: title.trim().isEmpty ? 'Untitled Song' : title.trim(),
          analysisEngine: widget.analysisEngine,
        ),
      ),
    ).then((_) => _loadRecentSongs());
  }

  // --- YouTube Extraction Flow ---

  String _cleanYouTubeTitle(String raw) {
    if (raw.trim().isEmpty) return '';
    var clean = raw.split(RegExp(r'[|–-]')).first.trim();
    clean = clean.replaceAll(
      RegExp(r'\((official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\)', caseSensitive: false),
      '',
    );
    clean = clean.replaceAll(
      RegExp(r'\[(official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\]', caseSensitive: false),
      '',
    );
    return clean.trim().isNotEmpty ? clean.trim() : raw.trim();
  }

  Future<void> _handlePasteYtUrl() async {
    final clipboardData = await Clipboard.getData(Clipboard.kTextPlain);
    if (clipboardData?.text != null && clipboardData!.text!.isNotEmpty) {
      _ytUrlController.text = clipboardData.text!.trim();
      _fetchYouTubeInfo();
    }
  }

  Future<void> _fetchYouTubeInfo() async {
    final url = _ytUrlController.text.trim();
    if (url.isEmpty) return;

    setState(() {
      _isFetchingYtInfo = true;
      _ytError = null;
      _ytMeta = null;
    });

    try {
      final meta = await YouTubeDownloaderService.fetchVideoDetails(url);
      setState(() {
        _ytMeta = meta;
        _songTitle = _cleanYouTubeTitle(meta.title);
        _isFetchingYtInfo = false;
      });
    } catch (e) {
      setState(() {
        _ytError = 'Could not load YouTube video: ${e.toString().replaceAll("Exception: ", "")}';
        _isFetchingYtInfo = false;
      });
    }
  }

  Future<void> _downloadAndAnalyzeYouTube() async {
    final url = _ytUrlController.text.trim();
    if (url.isEmpty || _ytMeta == null) return;

    setState(() {
      _isDownloadingYtAudio = true;
      _ytDownloadProgress = 0.05;
      _ytDownloadStatus = 'Connecting to YouTube...';
    });

    try {
      final audioFile = await YouTubeDownloaderService.downloadAudio(
        url,
        onProgress: (progress, status) {
          if (mounted) {
            setState(() {
              _ytDownloadProgress = progress;
              _ytDownloadStatus = status;
            });
          }
        },
      );

      if (mounted) {
        setState(() {
          _isDownloadingYtAudio = false;
        });
        _startAnalysisWithFile(audioFile, _songTitle);
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _isDownloadingYtAudio = false;
          _ytError = 'Download failed: ${e.toString().replaceAll("Exception: ", "")}';
        });
      }
    }
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
              ).then((_) => setState(() {}));
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Active Server Connection Mode Banner
            _buildServerConnectionBanner(),

            // Mode Selector Toggle
            Container(
              decoration: BoxDecoration(
                color: Colors.grey.shade200,
                borderRadius: BorderRadius.circular(12),
              ),
              padding: const EdgeInsets.all(4),
              child: Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _inputMode = 'file'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: _inputMode == 'file' ? Colors.white : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                          boxShadow: _inputMode == 'file'
                              ? [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 4, offset: const Offset(0, 1))]
                              : null,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.folder_open,
                              size: 18,
                              color: _inputMode == 'file' ? Colors.indigo : Colors.grey.shade700,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'Local Audio File',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: _inputMode == 'file' ? Colors.indigo : Colors.grey.shade700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _inputMode = 'youtube'),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: _inputMode == 'youtube' ? Colors.white : Colors.transparent,
                          borderRadius: BorderRadius.circular(8),
                          boxShadow: _inputMode == 'youtube'
                              ? [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 4, offset: const Offset(0, 1))]
                              : null,
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.play_circle_fill,
                              size: 18,
                              color: _inputMode == 'youtube' ? Colors.red.shade600 : Colors.grey.shade700,
                            ),
                            const SizedBox(width: 6),
                            Text(
                              'YouTube Link',
                              style: TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.bold,
                                color: _inputMode == 'youtube' ? Colors.red.shade600 : Colors.grey.shade700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Hero Card: File Mode vs YouTube Mode
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
              color: Colors.white,
              child: Padding(
                padding: const EdgeInsets.all(20.0),
                child: _inputMode == 'file' ? _buildFileContent() : _buildYouTubeContent(),
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
                    'No analyzed songs yet. Select an audio file or YouTube link above to begin!',
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

  // --- Local File Widget Sub-tree ---

  Widget _buildFileContent() {
    return Column(
      children: [
        CircleAvatar(
          radius: 36,
          backgroundColor: Colors.indigo.shade50,
          child: Icon(Icons.audio_file, size: 40, color: Colors.indigo.shade600),
        ),
        const SizedBox(height: 12),
        const Text(
          'Local Audio File Analysis',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 6),
        Text(
          'Select any MP3, WAV, FLAC, or M4A file from your phone storage.',
          style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 20),

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
              color: Colors.indigo.shade50.withValues(alpha: 0.5),
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
            onPressed: () => _startAnalysisWithFile(_selectedAudioFile!, _songTitle),
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
    );
  }

  // --- YouTube Widget Sub-tree ---

  Widget _buildYouTubeContent() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Center(
          child: CircleAvatar(
            radius: 36,
            backgroundColor: Colors.red.shade50,
            child: Icon(Icons.smart_display_rounded, size: 40, color: Colors.red.shade600),
          ),
        ),
        const SizedBox(height: 12),
        const Text(
          'Analyze Song from YouTube',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 6),
        Text(
          'Paste any YouTube video or shorts link. The audio stream is extracted directly on your device.',
          style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 18),

        // URL Input Field + Paste Button
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _ytUrlController,
                decoration: InputDecoration(
                  hintText: 'https://youtu.be/... or youtube.com/watch?v=...',
                  prefixIcon: const Icon(Icons.link, color: Colors.grey),
                  suffixIcon: _ytUrlController.text.isNotEmpty
                      ? IconButton(
                          icon: const Icon(Icons.clear, size: 18),
                          onPressed: () {
                            _ytUrlController.clear();
                            setState(() {
                              _ytMeta = null;
                              _ytError = null;
                            });
                          },
                        )
                      : null,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                  contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                  isDense: true,
                ),
                onSubmitted: (_) => _fetchYouTubeInfo(),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filledTonal(
              tooltip: 'Paste from clipboard',
              icon: const Icon(Icons.content_paste),
              onPressed: _handlePasteYtUrl,
            ),
          ],
        ),
        const SizedBox(height: 12),

        // Fetch / Validate Button
        if (_ytMeta == null && !_isFetchingYtInfo)
          OutlinedButton.icon(
            style: OutlinedButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: _fetchYouTubeInfo,
            icon: const Icon(Icons.search),
            label: const Text('Inspect YouTube Link'),
          ),

        if (_isFetchingYtInfo)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
                SizedBox(width: 12),
                Text('Inspecting YouTube link...', style: TextStyle(fontSize: 13, color: Colors.grey)),
              ],
            ),
          ),

        if (_ytError != null)
          Container(
            margin: const EdgeInsets.only(top: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.red.shade50,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: Colors.red.shade200),
            ),
            child: Row(
              children: [
                Icon(Icons.error_outline, color: Colors.red.shade700, size: 20),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    _ytError!,
                    style: TextStyle(color: Colors.red.shade900, fontSize: 12),
                  ),
                ),
              ],
            ),
          ),

        // YouTube Metadata Preview Card
        if (_ytMeta != null) ...[
          const SizedBox(height: 14),
          Container(
            decoration: BoxDecoration(
              color: Colors.grey.shade50,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.grey.shade300),
            ),
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.network(
                        _ytMeta!.thumbnailUrl,
                        width: 110,
                        height: 70,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          width: 110,
                          height: 70,
                          color: Colors.grey.shade300,
                          child: const Icon(Icons.movie, color: Colors.grey),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _ytMeta!.author,
                            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.red.shade700),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            _ytMeta!.title,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold),
                          ),
                          if (_ytMeta!.duration != null) ...[
                            const SizedBox(height: 4),
                            Text(
                              'Duration: ${_ytMeta!.duration!.inMinutes}:${(_ytMeta!.duration!.inSeconds % 60).toString().padLeft(2, '0')}',
                              style: TextStyle(fontSize: 11, color: Colors.grey.shade600),
                            ),
                          ],
                        ],
                      ),
                    ),
                  ],
                ),
                const Divider(height: 20),

                // Editable Title
                TextFormField(
                  initialValue: _songTitle,
                  decoration: const InputDecoration(
                    labelText: 'Song Title (for Chord Sheet)',
                    border: OutlineInputBorder(),
                    isDense: true,
                  ),
                  onChanged: (val) => _songTitle = val,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Download Progress Bar (when downloading)
          if (_isDownloadingYtAudio) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.amber.shade50,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.amber.shade200),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        _ytDownloadStatus,
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.amber.shade900),
                      ),
                      Text(
                        '${(_ytDownloadProgress * 100).toStringAsFixed(0)}%',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.amber.shade900),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  LinearProgressIndicator(
                    value: _ytDownloadProgress,
                    backgroundColor: Colors.amber.shade100,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.amber.shade700),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],

          // Download & Analyze Action Button
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.red.shade600,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            onPressed: _isDownloadingYtAudio ? null : _downloadAndAnalyzeYouTube,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(_isDownloadingYtAudio ? Icons.hourglass_top : Icons.download_for_offline),
                const SizedBox(width: 8),
                Text(
                  _isDownloadingYtAudio ? 'DOWNLOADING AUDIO STREAM...' : 'EXTRACT AUDIO & ANALYZE',
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildServerConnectionBanner() {
    final cfg = ServerConfigService.instance.config;
    final isLocal = cfg.mode == ConnectionMode.local;
    final isRemote = cfg.mode == ConnectionMode.remote;
    final isAuto = cfg.mode == ConnectionMode.auto;

    final IconData icon = isLocal
        ? Icons.wifi
        : isRemote
            ? Icons.cloud_outlined
            : Icons.auto_mode;

    final String modeLabel = isLocal
        ? 'LOCAL NETWORK'
        : isRemote
            ? 'REMOTE INTERNET'
            : 'AUTO DETECT';

    final String url = isRemote ? cfg.remoteUrl : cfg.localUrl;
    final String displayUrl = url.isNotEmpty ? url : 'Not configured';

    final color = isRemote ? Colors.teal : isAuto ? Colors.purple : Colors.indigo;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.shade50,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.shade200),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: color.shade700),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Connected via: $modeLabel',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    color: color.shade900,
                  ),
                ),
                Text(
                  displayUrl,
                  style: TextStyle(
                    fontSize: 10,
                    color: Colors.grey.shade700,
                    fontFamily: 'monospace',
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.settings, size: 18),
            tooltip: 'Configure Server',
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: () {
              Navigator.of(context).push(
                MaterialPageRoute(builder: (context) => const SettingsScreen()),
              ).then((_) => setState(() {}));
            },
          ),
        ],
      ),
    );
  }
}
