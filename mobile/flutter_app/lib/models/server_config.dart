enum ConnectionMode {
  local,
  remote,
  auto;

  String get label {
    switch (this) {
      case ConnectionMode.local:
        return 'Local Network';
      case ConnectionMode.remote:
        return 'Remote Internet';
      case ConnectionMode.auto:
        return 'Auto Detect';
    }
  }

  String get description {
    switch (this) {
      case ConnectionMode.local:
        return 'Direct LAN Wi-Fi connection to laptop. Works without internet.';
      case ConnectionMode.remote:
        return 'Cloudflare Tunnel over 4G/5G/external Wi-Fi. Laptop must be online.';
      case ConnectionMode.auto:
        return 'Tries Local Network first; falls back to Remote Internet seamlessly.';
    }
  }
}

class ServerConfig {
  final ConnectionMode mode;
  final String localUrl;
  final String remoteUrl;
  final String apiKey;
  final String? activeUrl;
  final ConnectionMode? activeMode;

  const ServerConfig({
    this.mode = ConnectionMode.local,
    this.localUrl = 'http://192.168.0.180:8000',
    this.remoteUrl = '',
    this.apiKey = '',
    this.activeUrl,
    this.activeMode,
  });

  ServerConfig copyWith({
    ConnectionMode? mode,
    String? localUrl,
    String? remoteUrl,
    String? apiKey,
    String? activeUrl,
    ConnectionMode? activeMode,
  }) {
    return ServerConfig(
      mode: mode ?? this.mode,
      localUrl: localUrl ?? this.localUrl,
      remoteUrl: remoteUrl ?? this.remoteUrl,
      apiKey: apiKey ?? this.apiKey,
      activeUrl: activeUrl ?? this.activeUrl,
      activeMode: activeMode ?? this.activeMode,
    );
  }

  Map<String, String> getHeaders() {
    final headers = <String, String>{};
    if (apiKey.trim().isNotEmpty) {
      headers['X-API-Key'] = apiKey.trim();
    }
    return headers;
  }
}

class HealthCheckResult {
  final bool isConnected;
  final int latencyMs;
  final String? status;
  final String? apiVersion;
  final String? analysisEngine;
  final bool analysisEngineAvailable;
  final String? device;
  final bool cudaAvailable;
  final int? cpuCount;
  final String? errorMessage;
  final ConnectionMode testedMode;
  final String url;

  const HealthCheckResult({
    required this.isConnected,
    this.latencyMs = 0,
    this.status,
    this.apiVersion,
    this.analysisEngine,
    this.analysisEngineAvailable = false,
    this.device,
    this.cudaAvailable = false,
    this.cpuCount,
    this.errorMessage,
    required this.testedMode,
    required this.url,
  });

  factory HealthCheckResult.success({
    required int latencyMs,
    required Map<String, dynamic> data,
    required ConnectionMode mode,
    required String url,
  }) {
    return HealthCheckResult(
      isConnected: true,
      latencyMs: latencyMs,
      status: data['status']?.toString() ?? 'healthy',
      apiVersion: data['api_version']?.toString() ?? '1.0.0',
      analysisEngine: data['analysis_engine']?.toString() ?? 'WindowsAnalysisEngine',
      analysisEngineAvailable: data['analysis_engine_available'] == true,
      device: data['device']?.toString() ?? 'CPU',
      cudaAvailable: data['cuda_available'] == true,
      cpuCount: data['cpu_count'] is int ? data['cpu_count'] as int : null,
      testedMode: mode,
      url: url,
    );
  }

  factory HealthCheckResult.failure({
    required String errorMessage,
    required ConnectionMode mode,
    required String url,
    int latencyMs = 0,
  }) {
    return HealthCheckResult(
      isConnected: false,
      errorMessage: errorMessage,
      testedMode: mode,
      url: url,
      latencyMs: latencyMs,
    );
  }
}
