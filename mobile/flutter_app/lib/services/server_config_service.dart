import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../models/server_config.dart';

class ServerConfigService extends ChangeNotifier {
  static const String _keyMode = 'server_connection_mode';
  static const String _keyLocalUrl = 'server_local_url';
  static const String _keyRemoteUrl = 'server_remote_url';
  static const String _keyApiKey = 'server_api_key';

  // Legacy key for backwards compatibility
  static const String _legacyKeyDevUrl = 'dev_server_url';

  static ServerConfigService? _instance;
  static ServerConfigService get instance => _instance ??= ServerConfigService._();

  ServerConfig _config = const ServerConfig();
  bool _isInitialized = false;

  ServerConfig get config => _config;
  bool get isInitialized => _isInitialized;

  ServerConfigService._();

  Future<void> init() async {
    if (_isInitialized) return;
    final prefs = await SharedPreferences.getInstance();

    final savedModeStr = prefs.getString(_keyMode);
    ConnectionMode mode = ConnectionMode.local;
    if (savedModeStr == 'remote') {
      mode = ConnectionMode.remote;
    } else if (savedModeStr == 'auto') {
      mode = ConnectionMode.auto;
    }

    const compileEnvUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');

    // Fallbacks
    final legacyUrl = prefs.getString(_legacyKeyDevUrl);
    final savedLocalUrl = prefs.getString(_keyLocalUrl);
    final savedRemoteUrl = prefs.getString(_keyRemoteUrl);
    final savedApiKey = prefs.getString(_keyApiKey) ?? '';

    String initialLocalUrl;
    if (savedLocalUrl != null && savedLocalUrl.isNotEmpty) {
      initialLocalUrl = savedLocalUrl;
    } else if (legacyUrl != null && legacyUrl.isNotEmpty && !legacyUrl.startsWith('https://')) {
      initialLocalUrl = legacyUrl;
    } else {
      initialLocalUrl = 'http://192.168.0.180:8000';
    }

    String initialRemoteUrl;
    if (savedRemoteUrl != null && savedRemoteUrl.isNotEmpty) {
      initialRemoteUrl = savedRemoteUrl;
    } else if (compileEnvUrl.startsWith('https://')) {
      initialRemoteUrl = compileEnvUrl;
    } else if (legacyUrl != null && legacyUrl.startsWith('https://')) {
      initialRemoteUrl = legacyUrl;
    } else {
      initialRemoteUrl = '';
    }

    _config = ServerConfig(
      mode: mode,
      localUrl: _sanitizeUrl(initialLocalUrl),
      remoteUrl: _sanitizeUrl(initialRemoteUrl),
      apiKey: savedApiKey,
      activeUrl: mode == ConnectionMode.remote ? initialRemoteUrl : initialLocalUrl,
      activeMode: mode == ConnectionMode.remote ? ConnectionMode.remote : ConnectionMode.local,
    );

    _isInitialized = true;
    notifyListeners();
  }

  Future<void> updateConfig({
    ConnectionMode? mode,
    String? localUrl,
    String? remoteUrl,
    String? apiKey,
  }) async {
    final prefs = await SharedPreferences.getInstance();

    final newMode = mode ?? _config.mode;
    final newLocal = localUrl != null ? _sanitizeUrl(localUrl) : _config.localUrl;
    final newRemote = remoteUrl != null ? _sanitizeUrl(remoteUrl) : _config.remoteUrl;
    final newApiKey = apiKey ?? _config.apiKey;

    await prefs.setString(_keyMode, newMode.name);
    await prefs.setString(_keyLocalUrl, newLocal);
    await prefs.setString(_keyRemoteUrl, newRemote);
    await prefs.setString(_keyApiKey, newApiKey);

    // Also update legacy key so existing components don't break
    final active = newMode == ConnectionMode.remote ? newRemote : newLocal;
    await prefs.setString(_legacyKeyDevUrl, active);

    _config = _config.copyWith(
      mode: newMode,
      localUrl: newLocal,
      remoteUrl: newRemote,
      apiKey: newApiKey,
      activeUrl: active,
      activeMode: newMode == ConnectionMode.remote ? ConnectionMode.remote : ConnectionMode.local,
    );

    notifyListeners();
  }

  /// Resolves the effective base URL according to the current mode (or probes in Auto mode).
  Future<String> resolveActiveUrl() async {
    if (!_isInitialized) await init();

    if (_config.mode == ConnectionMode.local) {
      final url = _config.localUrl.isNotEmpty ? _config.localUrl : 'http://192.168.0.180:8000';
      _config = _config.copyWith(activeUrl: url, activeMode: ConnectionMode.local);
      return url;
    }

    if (_config.mode == ConnectionMode.remote) {
      if (_config.remoteUrl.isEmpty) {
        throw Exception(
          'Remote Internet URL is not configured.\n'
          'Please open Settings and enter the Cloudflare Tunnel HTTPS URL.',
        );
      }
      _config = _config.copyWith(activeUrl: _config.remoteUrl, activeMode: ConnectionMode.remote);
      return _config.remoteUrl;
    }

    // AUTO MODE: Probe local first (fast timeout), then remote.
    final localUrl = _config.localUrl;
    final remoteUrl = _config.remoteUrl;

    if (localUrl.isNotEmpty) {
      try {
        final localHealth = await testHealth(
          localUrl,
          ConnectionMode.local,
          timeout: const Duration(milliseconds: 1800),
        );
        if (localHealth.isConnected) {
          _config = _config.copyWith(activeUrl: localUrl, activeMode: ConnectionMode.local);
          notifyListeners();
          return localUrl;
        }
      } catch (_) {}
    }

    if (remoteUrl.isNotEmpty) {
      try {
        final remoteHealth = await testHealth(
          remoteUrl,
          ConnectionMode.remote,
          timeout: const Duration(milliseconds: 2500),
        );
        if (remoteHealth.isConnected) {
          _config = _config.copyWith(activeUrl: remoteUrl, activeMode: ConnectionMode.remote);
          notifyListeners();
          return remoteUrl;
        }
      } catch (_) {}
    }

    // Both failed
    throw Exception(
      'Analysis server unavailable.\n'
      '• Local Network ($localUrl): Not reachable (Check Wi-Fi and FastAPI)\n'
      '• Remote Internet ($remoteUrl): Not reachable (Check laptop, internet, and Cloudflare Tunnel)\n\n'
      'Please open Settings to check connection status.',
    );
  }

  /// Performs a health check against a given URL.
  Future<HealthCheckResult> testHealth(
    String rawUrl,
    ConnectionMode mode, {
    Duration timeout = const Duration(seconds: 4),
    String? apiKey,
  }) async {
    final url = _sanitizeUrl(rawUrl);
    if (url.isEmpty) {
      return HealthCheckResult.failure(
        errorMessage: 'URL is empty. Please enter a valid server URL.',
        mode: mode,
        url: url,
      );
    }

    final effectiveKey = apiKey ?? _config.apiKey;
    final headers = <String, String>{};
    if (effectiveKey.trim().isNotEmpty) {
      headers['X-API-Key'] = effectiveKey.trim();
    }

    final stopwatch = Stopwatch()..start();
    try {
      final uri = Uri.parse('$url/api/health');
      http.Response res;
      try {
        res = await http.get(uri, headers: headers).timeout(timeout);
      } catch (_) {
        // Fallback to /health
        final fallbackUri = Uri.parse('$url/health');
        res = await http.get(fallbackUri, headers: headers).timeout(timeout);
      }
      stopwatch.stop();

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        return HealthCheckResult.success(
          latencyMs: stopwatch.elapsedMilliseconds,
          data: data,
          mode: mode,
          url: url,
        );
      } else if (res.statusCode == 401 || res.statusCode == 403) {
        return HealthCheckResult.failure(
          errorMessage: 'Authentication failed (HTTP ${res.statusCode}). Invalid or missing API key.',
          mode: mode,
          url: url,
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      } else {
        return HealthCheckResult.failure(
          errorMessage: 'Server returned HTTP ${res.statusCode}: ${res.body}',
          mode: mode,
          url: url,
          latencyMs: stopwatch.elapsedMilliseconds,
        );
      }
    } on SocketException catch (e) {
      stopwatch.stop();
      final reason = mode == ConnectionMode.local
          ? 'Cannot reach local server.\n• Confirm phone and laptop are on the same Wi-Fi.\n• Verify FastAPI is running on port 8000.\n• Check Windows Firewall allows port 8000.'
          : 'Cannot reach remote server.\n• Confirm laptop is ON and connected to internet.\n• Verify Cloudflare Tunnel is running.\n• Check remote tunnel URL in Settings.';
      return HealthCheckResult.failure(
        errorMessage: '$reason\n(Details: ${e.message})',
        mode: mode,
        url: url,
        latencyMs: stopwatch.elapsedMilliseconds,
      );
    } on TimeoutException {
      stopwatch.stop();
      return HealthCheckResult.failure(
        errorMessage: 'Connection timed out after ${timeout.inSeconds}s. Host did not respond in time.',
        mode: mode,
        url: url,
        latencyMs: stopwatch.elapsedMilliseconds,
      );
    } catch (e) {
      stopwatch.stop();
      return HealthCheckResult.failure(
        errorMessage: 'Connection failed: $e',
        mode: mode,
        url: url,
        latencyMs: stopwatch.elapsedMilliseconds,
      );
    }
  }

  static String _sanitizeUrl(String url) {
    var trimmed = url.trim();
    while (trimmed.endsWith('/')) {
      trimmed = trimmed.substring(0, trimmed.length - 1);
    }
    return trimmed;
  }
}
