import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _serverController = TextEditingController();
  bool _isTesting = false;
  String? _testResult;
  bool _testSuccess = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _serverController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _serverController.text = prefs.getString('dev_server_url') ?? 'http://10.0.2.2:8000';
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final url = _serverController.text.trim().replaceAll(RegExp(r'/+$'), '');
    await prefs.setString('dev_server_url', url);
    await prefs.setString('engine_mode', 'server');
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Server configuration saved successfully')),
      );
    }
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTesting = true;
      _testResult = null;
      _testSuccess = false;
    });

    try {
      final url = _serverController.text.trim().replaceAll(RegExp(r'/+$'), '');
      http.Response res;
      try {
        res = await http.get(Uri.parse('$url/api/health')).timeout(const Duration(seconds: 4));
      } catch (_) {
        res = await http.get(Uri.parse('$url/health')).timeout(const Duration(seconds: 4));
      }

      if (res.statusCode == 200) {
        String device = '';
        try {
          final data = jsonDecode(res.body);
          if (data is Map && data['device'] != null) {
            device = ' (Device: ${data['device']})';
          }
        } catch (_) {}
        setState(() {
          _testSuccess = true;
          _testResult = 'Connected to Analysis Server successfully!$device ✓';
        });
      } else {
        setState(() {
          _testSuccess = false;
          _testResult = 'Server returned HTTP ${res.statusCode}';
        });
      }
    } catch (e) {
      setState(() {
        _testSuccess = false;
        _testResult = 'Connection failed: $e';
      });
    } finally {
      setState(() => _isTesting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Engine Information
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(Icons.hub, color: Colors.indigo),
                      SizedBox(width: 8),
                      Text(
                        'Authoritative MIR Engine',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ],
                  ),
                  SizedBox(height: 8),
                  Text(
                    'High-Fidelity Windows MIR & Automatic Chord Recognition Server (BTC Transformer + Demucs v4 + BassStem Inversion Tracking). All musical attributes (key, tempo, meter, beat grid, chord sheet) are computed authoritatively by the backend.',
                    style: TextStyle(fontSize: 13, color: Colors.black87),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Server Connection config
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'FastAPI Server URL',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    '• Android Emulator: http://10.0.2.2:8000\n• Physical Phone / LAN: http://<PC_IP>:8000\n• Desktop / Local: http://127.0.0.1:8000',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 14),
                  TextField(
                    controller: _serverController,
                    decoration: const InputDecoration(
                      border: OutlineInputBorder(),
                      labelText: 'Analysis Server Base URL',
                      prefixIcon: Icon(Icons.link),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      ElevatedButton.icon(
                        onPressed: _isTesting ? null : _testConnection,
                        icon: _isTesting
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.wifi_tethering),
                        label: const Text('Test Connection'),
                      ),
                      const Spacer(),
                      ElevatedButton(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.indigo,
                          foregroundColor: Colors.white,
                        ),
                        onPressed: _saveSettings,
                        child: const Text('Save'),
                      ),
                    ],
                  ),
                  if (_testResult != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: _testSuccess ? Colors.green.shade50 : Colors.red.shade50,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: _testSuccess ? Colors.green.shade300 : Colors.red.shade300,
                        ),
                      ),
                      child: Text(
                        _testResult!,
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: _testSuccess ? Colors.green.shade900 : Colors.red.shade900,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),

          const SizedBox(height: 16),
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Song Chord Analyzer Client', style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 4),
                  Text('Version 1.0.0 (Client Edition)', style: TextStyle(color: Colors.grey)),
                  SizedBox(height: 8),
                  Text(
                    'Offline chord sheet rendering, audio-synchronized playback highlighting, local SQLite history storage, and ReportLab-compatible PDF exports.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
