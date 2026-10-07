import 'package:flutter/material.dart';
import '../models/server_config.dart';
import '../services/server_config_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final ServerConfigService _configService = ServerConfigService.instance;

  late ConnectionMode _selectedMode;
  final TextEditingController _localController = TextEditingController();
  final TextEditingController _remoteController = TextEditingController();
  final TextEditingController _apiKeyController = TextEditingController();

  bool _isTesting = false;
  HealthCheckResult? _lastHealthResult;
  HealthCheckResult? _lastSecondaryHealthResult; // for Auto mode

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  @override
  void dispose() {
    _localController.dispose();
    _remoteController.dispose();
    _apiKeyController.dispose();
    super.dispose();
  }

  Future<void> _loadSettings() async {
    await _configService.init();
    final cfg = _configService.config;
    setState(() {
      _selectedMode = cfg.mode;
      _localController.text = cfg.localUrl;
      _remoteController.text = cfg.remoteUrl;
      _apiKeyController.text = cfg.apiKey;
    });
  }

  Future<void> _saveSettings() async {
    await _configService.updateConfig(
      mode: _selectedMode,
      localUrl: _localController.text.trim(),
      remoteUrl: _remoteController.text.trim(),
      apiKey: _apiKeyController.text.trim(),
    );

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Configuration saved for ${_selectedMode.label}'),
          backgroundColor: Colors.indigo,
        ),
      );
    }
  }

  Future<void> _runConnectionTest() async {
    setState(() {
      _isTesting = true;
      _lastHealthResult = null;
      _lastSecondaryHealthResult = null;
    });

    try {
      final localUrl = _localController.text.trim();
      final remoteUrl = _remoteController.text.trim();
      final key = _apiKeyController.text.trim();

      if (_selectedMode == ConnectionMode.local) {
        final result = await _configService.testHealth(
          localUrl,
          ConnectionMode.local,
          apiKey: key,
        );
        setState(() => _lastHealthResult = result);
      } else if (_selectedMode == ConnectionMode.remote) {
        final result = await _configService.testHealth(
          remoteUrl,
          ConnectionMode.remote,
          apiKey: key,
        );
        setState(() => _lastHealthResult = result);
      } else {
        // AUTO MODE: test both
        final localResult = await _configService.testHealth(
          localUrl,
          ConnectionMode.local,
          apiKey: key,
        );
        final remoteResult = await _configService.testHealth(
          remoteUrl,
          ConnectionMode.remote,
          apiKey: key,
        );
        setState(() {
          _lastHealthResult = localResult;
          _lastSecondaryHealthResult = remoteResult;
        });
      }
    } finally {
      if (mounted) {
        setState(() => _isTesting = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Analysis Server Settings'),
        actions: [
          IconButton(
            icon: const Icon(Icons.check),
            tooltip: 'Save Settings',
            onPressed: _saveSettings,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Authoritative Engine Info Card
          _buildEngineInfoCard(),
          const SizedBox(height: 16),

          // Connection Mode Selector
          _buildModeSelectorCard(),
          const SizedBox(height: 16),

          // Server URLs & Credentials Card
          _buildUrlConfigCard(),
          const SizedBox(height: 16),

          // Diagnostics Panel
          _buildDiagnosticsCard(),
          const SizedBox(height: 24),

          // Save Button
          ElevatedButton.icon(
            onPressed: _saveSettings,
            icon: const Icon(Icons.save),
            label: const Text('Save Server Configuration'),
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.indigo,
              foregroundColor: Colors.white,
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }

  Widget _buildEngineInfoCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: const Padding(
        padding: EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.hub_outlined, color: Colors.indigo),
                SizedBox(width: 8),
                Text(
                  'Authoritative Windows MIR Engine',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ],
            ),
            SizedBox(height: 8),
            Text(
              'All key, meter, beat grid, and chord analyses are computed by the authoritative Python MIR server on your laptop. Dual modes allow seamless access either on local Wi-Fi or remotely over the internet via Cloudflare Tunnel.',
              style: TextStyle(fontSize: 13, color: Colors.black87),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildModeSelectorCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Connection Mode',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 4),
            Text(
              _selectedMode.description,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade700),
            ),
            const SizedBox(height: 12),
            SegmentedButton<ConnectionMode>(
              segments: const [
                ButtonSegment<ConnectionMode>(
                  value: ConnectionMode.local,
                  icon: Icon(Icons.wifi),
                  label: Text('Local'),
                ),
                ButtonSegment<ConnectionMode>(
                  value: ConnectionMode.remote,
                  icon: Icon(Icons.cloud),
                  label: Text('Remote'),
                ),
                ButtonSegment<ConnectionMode>(
                  value: ConnectionMode.auto,
                  icon: Icon(Icons.auto_mode),
                  label: Text('Auto'),
                ),
              ],
              selected: {_selectedMode},
              onSelectionChanged: (newSelection) {
                setState(() {
                  _selectedMode = newSelection.first;
                  _lastHealthResult = null;
                  _lastSecondaryHealthResult = null;
                });
              },
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildUrlConfigCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Endpoint Configuration',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 12),

            // Local Network URL Field
            if (_selectedMode == ConnectionMode.local || _selectedMode == ConnectionMode.auto) ...[
              TextField(
                controller: _localController,
                decoration: InputDecoration(
                  labelText: 'Local Network URL (Wi-Fi / LAN)',
                  hintText: 'http://192.168.0.180:8000',
                  prefixIcon: const Icon(Icons.wifi, color: Colors.indigo),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  helperText: 'Laptop IP on local Wi-Fi. (Port 8000)',
                ),
                keyboardType: TextInputType.url,
              ),
              const SizedBox(height: 16),
            ],

            // Remote Tunnel URL Field
            if (_selectedMode == ConnectionMode.remote || _selectedMode == ConnectionMode.auto) ...[
              TextField(
                controller: _remoteController,
                decoration: InputDecoration(
                  labelText: 'Remote Internet URL (Cloudflare Tunnel)',
                  hintText: 'https://xxx.trycloudflare.com',
                  prefixIcon: const Icon(Icons.cloud_queue, color: Colors.teal),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                  helperText: 'Public HTTPS tunnel URL to your laptop.',
                ),
                keyboardType: TextInputType.url,
              ),
              const SizedBox(height: 16),
            ],

            // Security API Key Field
            TextField(
              controller: _apiKeyController,
              decoration: InputDecoration(
                labelText: 'API Key (Optional Security Token)',
                hintText: 'Leave empty for open local dev',
                prefixIcon: const Icon(Icons.vpn_key_outlined, color: Colors.amber),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(8)),
                helperText: 'Protects remote tunnel from unauthorized access.',
              ),
            ),
            const SizedBox(height: 16),

            // Test Connection Button
            OutlinedButton.icon(
              onPressed: _isTesting ? null : _runConnectionTest,
              icon: _isTesting
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.network_check),
              label: Text(_isTesting ? 'Testing Health...' : 'Test Connection'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.indigo,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDiagnosticsCard() {
    return Card(
      elevation: 1,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.analytics_outlined, color: Colors.indigo),
                const SizedBox(width: 8),
                const Text(
                  'Connection Diagnostics',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: Colors.indigo.shade50,
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    _selectedMode.label.toUpperCase(),
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.indigo.shade800),
                  ),
                ),
              ],
            ),
            const Divider(height: 24),

            _buildDiagRow('Configured Local:', _localController.text.trim().isEmpty ? 'None' : _localController.text.trim()),
            _buildDiagRow('Configured Remote:', _remoteController.text.trim().isEmpty ? 'None' : _remoteController.text.trim()),
            _buildDiagRow(
              'Active Endpoint:',
              _selectedMode == ConnectionMode.remote
                  ? (_remoteController.text.trim().isEmpty ? 'Not Set' : _remoteController.text.trim())
                  : (_localController.text.trim().isEmpty ? 'Not Set' : _localController.text.trim()),
            ),
            const SizedBox(height: 12),

            // Health Result display
            if (_lastHealthResult != null) ...[
              _buildHealthCheckResultBadge(_lastHealthResult!),
              if (_lastSecondaryHealthResult != null) ...[
                const SizedBox(height: 8),
                _buildHealthCheckResultBadge(_lastSecondaryHealthResult!),
              ],
            ] else ...[
              Row(
                children: [
                  Icon(Icons.info_outline, size: 16, color: Colors.grey.shade600),
                  const SizedBox(width: 6),
                  Text(
                    'Tap "Test Connection" to verify server availability.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildDiagRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(
              label,
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Colors.black87),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(fontSize: 12, color: Colors.grey.shade800, fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHealthCheckResultBadge(HealthCheckResult result) {
    final isSuccess = result.isConnected;
    final color = isSuccess ? Colors.green.shade700 : Colors.red.shade700;
    final bgColor = isSuccess ? Colors.green.shade50 : Colors.red.shade50;

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(isSuccess ? Icons.check_circle : Icons.error, color: color, size: 18),
              const SizedBox(width: 8),
              Text(
                '${result.testedMode.label}: ${isSuccess ? "CONNECTED" : "DISCONNECTED"}',
                style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: color),
              ),
              const Spacer(),
              if (isSuccess)
                Text(
                  '${result.latencyMs} ms',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: color),
                ),
            ],
          ),
          const SizedBox(height: 6),
          if (isSuccess) ...[
            Text('• Analysis Engine: ${result.analysisEngine ?? "Ready"}', style: const TextStyle(fontSize: 12)),
            Text('• Device Hardware: ${result.device ?? "CPU"} (CUDA: ${result.cudaAvailable ? "Yes" : "No"})', style: const TextStyle(fontSize: 12)),
            Text('• API Version: ${result.apiVersion ?? "1.0.0"}', style: const TextStyle(fontSize: 12)),
          ] else ...[
            Text(
              result.errorMessage ?? 'Connection failed.',
              style: TextStyle(fontSize: 12, color: color),
            ),
          ],
        ],
      ),
    );
  }
}
