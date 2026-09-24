import 'package:flutter/material.dart';
import '../models/history_song.dart';
import '../services/history_service.dart';
import '../services/analysis_engine.dart';
import 'chord_sheet_screen.dart';

class HistoryScreen extends StatefulWidget {
  final AnalysisEngine analysisEngine;

  const HistoryScreen({
    super.key,
    required this.analysisEngine,
  });

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  List<HistorySong> _songs = [];
  bool _isLoading = true;
  String _searchQuery = '';
  String _sortBy = 'last_opened_at';
  bool _ascending = false;

  @override
  void initState() {
    super.initState();
    _fetchSongs();
  }

  Future<void> _fetchSongs() async {
    setState(() => _isLoading = true);
    final songs = await HistoryService.getSongs(
      searchQuery: _searchQuery,
      sortBy: _sortBy,
      ascending: _ascending,
    );
    setState(() {
      _songs = songs;
      _isLoading = false;
    });
  }

  Future<void> _openSong(HistorySong song) async {
    final analysis = await HistoryService.loadAnalysis(song.id);
    if (analysis != null && mounted) {
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (context) => ChordSheetScreen(
            initialAnalysis: analysis,
            analysisEngine: widget.analysisEngine,
          ),
        ),
      ).then((_) => _fetchSongs());
    }
  }

  Future<void> _deleteSong(HistorySong song) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Song?'),
        content: Text('Are you sure you want to delete "${song.title}" from your library?'),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(false), child: const Text('Cancel')),
          TextButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );

    if (confirm == true) {
      await HistoryService.deleteSong(song.id);
      _fetchSongs();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.grey.shade50,
      appBar: AppBar(
        title: const Text('Song Library / History'),
      ),
      body: Column(
        children: [
          // Search & Filter Bar
          Padding(
            padding: const EdgeInsets.all(12.0),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    decoration: InputDecoration(
                      hintText: 'Search songs, keys, artists...',
                      prefixIcon: const Icon(Icons.search, size: 20),
                      isDense: true,
                      contentPadding: const EdgeInsets.symmetric(vertical: 10),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    onChanged: (val) {
                      _searchQuery = val;
                      _fetchSongs();
                    },
                  ),
                ),
                const SizedBox(width: 8),
                PopupMenuButton<String>(
                  icon: const Icon(Icons.sort),
                  tooltip: 'Sort By',
                  onSelected: (val) {
                    setState(() {
                      if (val == 'title') {
                        _sortBy = 'title';
                        _ascending = true;
                      } else {
                        _sortBy = val;
                        _ascending = false;
                      }
                    });
                    _fetchSongs();
                  },
                  itemBuilder: (context) => const [
                    PopupMenuItem(value: 'last_opened_at', child: Text('Recently Opened')),
                    PopupMenuItem(value: 'created_at', child: Text('Recently Analyzed')),
                    PopupMenuItem(value: 'title', child: Text('Title (A-Z)')),
                  ],
                ),
              ],
            ),
          ),

          // Songs List
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _songs.isEmpty
                    ? Center(
                        child: Text(
                          _searchQuery.isEmpty
                              ? 'Your library is empty. Analyze a song to get started!'
                              : 'No songs matched your search.',
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _songs.length,
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        itemBuilder: (context, index) {
                          final song = _songs[index];
                          return Card(
                            elevation: 1,
                            margin: const EdgeInsets.only(bottom: 8),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            child: ListTile(
                              onTap: () => _openSong(song),
                              leading: CircleAvatar(
                                backgroundColor: Colors.indigo.shade100,
                                child: Text(
                                  song.keyDisplay.split(' ').first,
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: Colors.indigo.shade900,
                                  ),
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
                              trailing: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  IconButton(
                                    icon: Icon(
                                      song.isFavorite ? Icons.star : Icons.star_border,
                                      color: song.isFavorite ? Colors.amber : Colors.grey,
                                    ),
                                    onPressed: () async {
                                      await HistoryService.toggleFavorite(song.id, !song.isFavorite);
                                      _fetchSongs();
                                    },
                                  ),
                                  IconButton(
                                    icon: const Icon(Icons.delete_outline, size: 20, color: Colors.grey),
                                    onPressed: () => _deleteSong(song),
                                  ),
                                ],
                              ),
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
