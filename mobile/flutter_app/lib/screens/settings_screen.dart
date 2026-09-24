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
  String _engineMode = 'dev_http';
  bool _isTesting = false;
  String? _testResult;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    setState(() {
      _serverController.text = prefs.getString('dev_server_url') ?? 'http://10.0.2.2:8000';
      _engineMode = prefs.getString('engine_mode') ?? 'dev_http';
    });
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('dev_server_url', _serverController.text.trim());
    await prefs.setString('engine_mode', _engineMode);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Settings saved successfully')),
      );
    }
  }

  Future<void> _testConnection() async {
    setState(() {
      _isTesting = true;
      _testResult = null;
    });

    try {
      final url = _serverController.text.trim().replaceAll(RegExp(r'/+$'), '');
      final res = await http.get(Uri.parse('$url/api/history')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        setState(() => _testResult = 'Connected to SongChord backend successfully! ✓');
      } else {
        setState(() => _testResult = 'Server returned HTTP ${res.statusCode}');
      }
    } catch (e) {
      setState(() => _testResult = 'Connection failed: $e');
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
          // Engine Mode
          Card(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Analysis Engine Mode',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  RadioListTile<String>(
                    title: const Text('Development Server (Stage A)'),
                    subtitle: const Text('Sends audio to your local desktop/Wi-Fi analysis engine'),
                    value: 'dev_http',
                    groupValue: _engineMode,
                    onChanged: (val) => setState(() => _engineMode = val!),
                  ),
                  RadioListTile<String>(
                    title: const Text('Local On-Device ML (Stage B)'),
                    subtitle: const Text('Offline ONNX/ExecuTorch inference directly on ARM64'),
                    value: 'local_ml',
                    groupValue: _engineMode,
                    onChanged: (val) => setState(() => _engineMode = val!),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Server Connection config
          if (_engineMode == 'dev_http')
            Card(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Text(
                      'Development Server URL',
                      style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'For Android Emulator use: http://10.0.2.2:8000\nFor physical phone use your PC LAN IP: http://192.168.x.x:8000',
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                    ),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _serverController,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        labelText: 'Server Base URL',
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
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: _testResult!.contains('successfully')
                              ? Colors.green.shade50
                              : Colors.red.shade50,
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          _testResult!,
                          style: TextStyle(
                            fontSize: 12,
                            color: _testResult!.contains('successfully')
                                ? Colors.green.shade900
                                : Colors.red.shade900,
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
                  Text('Song Chord Analyzer Mobile', style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 4),
                  Text('Version 1.0.0 (ARM64)', style: TextStyle(color: Colors.grey)),
                  SizedBox(height: 8),
                  Text(
                    'Architected for high-fidelity music information retrieval, BTC Transformer chord recognition, sub-bass physical inversion tracking, and local-first song history.',
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
