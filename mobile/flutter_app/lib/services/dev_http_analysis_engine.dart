import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'analysis_engine.dart';
import 'transpose_service.dart';
import 'server_config_service.dart';
import '../models/server_config.dart';
import '../models/song_analysis.dart';
import '../models/analysis_status.dart';

class DevHttpAnalysisEngine implements AnalysisEngine {
  String baseUrl;
  final ServerConfigService? configService;

  DevHttpAnalysisEngine({
    String? baseUrl,
    this.configService,
  }) : baseUrl = baseUrl ??
            const String.fromEnvironment('API_BASE_URL',
                defaultValue: 'http://192.168.0.180:8000');

  void updateBaseUrl(String newUrl) {
    baseUrl = newUrl.replaceAll(RegExp(r'/+$'), '');
  }

  Future<String> _getEffectiveBaseUrl() async {
    if (configService != null) {
      try {
        final url = await configService!.resolveActiveUrl();
        baseUrl = url;
        return url;
      } catch (e) {
        // Fallback to currently held baseUrl if resolution throws
        if (baseUrl.isNotEmpty) return baseUrl;
        rethrow;
      }
    }
    return baseUrl;
  }

  Map<String, String> _getHeaders() {
    if (configService != null) {
      return configService!.config.getHeaders();
    }
    return {};
  }

  String _formatConnectionError(String url, Object error) {
    final mode = configService?.config.mode ?? ConnectionMode.local;
    if (mode == ConnectionMode.local) {
      return 'Local analysis server unavailable at $url.\n'
          '• Verify that your phone and laptop are on the same Wi-Fi.\n'
          '• Check that FastAPI is running on port 8000.\n'
          '• Check Windows Firewall settings.\n'
          'Details: $error';
    } else if (mode == ConnectionMode.remote) {
      return 'Remote analysis server unavailable at $url.\n'
          '• Verify that the laptop is ON and connected to the internet.\n'
          '• Verify that FastAPI and Cloudflare Tunnel are active.\n'
          'Details: $error';
    } else {
      return 'Analysis server unavailable in Auto mode.\n'
          'Neither Local nor Remote server could be reached.\n'
          'Details: $error';
    }
  }

  @override
  Future<String> startAnalysis({
    required File audioFile,
    required String songTitle,
  }) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final uri = Uri.parse('$effectiveUrl/api/analyze');
    final request = http.MultipartRequest('POST', uri);
    request.headers.addAll(_getHeaders());
    request.fields['title'] = songTitle;
    request.fields['song_title'] = songTitle;
    request.fields['force'] = 'true';
    request.files.add(await http.MultipartFile.fromPath(
      'file',
      audioFile.path,
      filename: audioFile.path.split(Platform.pathSeparator).last,
    ));

    http.Response response;
    try {
      final streamedResponse = await request.send().timeout(const Duration(seconds: 90));
      response = await http.Response.fromStream(streamedResponse).timeout(const Duration(seconds: 30));
    } on SocketException catch (e) {
      throw Exception(_formatConnectionError(effectiveUrl, e));
    } on TimeoutException catch (e) {
      throw Exception('Connection to analysis server at $effectiveUrl timed out while uploading audio.\nDetails: $e');
    } catch (e) {
      throw Exception(_formatConnectionError(effectiveUrl, e));
    }

    if (response.statusCode == 401 || response.statusCode == 403) {
      throw Exception('Server rejected request: Authentication failed (HTTP ${response.statusCode}). Please check API key in Settings.');
    }
    if (response.statusCode == 413) {
      throw Exception('Audio file exceeds the maximum allowed file size limit (500 MB).');
    }
    if (response.statusCode == 429) {
      throw Exception('Analysis queue is currently full. Please wait a moment and try again.');
    }
    if (response.statusCode != 200) {
      String detail = response.body;
      try {
        final errJson = jsonDecode(response.body);
        if (errJson is Map && errJson['detail'] != null) {
          detail = errJson['detail'].toString();
        }
      } catch (_) {}
      throw Exception('Server rejected analysis request (HTTP ${response.statusCode}): $detail');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;

    if (data['status'] == 'DUPLICATE_FOUND' && data['existing_song'] != null) {
      final existing = data['existing_song'] as Map<String, dynamic>;
      final existingId = existing['song_id'] ?? existing['id'];
      if (existingId != null) {
        return existingId.toString();
      }
    }

    final analysisId = data['analysis_id'] as String?;
    if (analysisId == null || analysisId.isEmpty) {
      throw Exception('Invalid server response: missing analysis_id in payload: ${response.body}');
    }
    return analysisId;
  }

  @override
  Future<AnalysisStatus> getStatus(String analysisId) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = _getHeaders();

    // Primary: status endpoint
    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/$analysisId/status');
      final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 8));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return AnalysisStatus.fromJson(data);
      }
    } catch (_) {
      // Try fallback below
    }

    // Fallback: unified analyze job endpoint
    try {
      final fallbackUri = Uri.parse('$effectiveUrl/analyze/$analysisId');
      final fallbackRes = await http.get(fallbackUri, headers: headers).timeout(const Duration(seconds: 8));
      if (fallbackRes.statusCode == 200) {
        final data = jsonDecode(fallbackRes.body) as Map<String, dynamic>;
        return AnalysisStatus.fromJson(data);
      }
    } catch (e) {
      throw Exception(_formatConnectionError(effectiveUrl, e));
    }

    throw Exception('Failed to get analysis status for $analysisId from $effectiveUrl');
  }

  @override
  Future<SongAnalysis> getResult(String analysisId) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = _getHeaders();

    // Primary: direct GET /api/analysis/{id}
    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/$analysisId');
      final response = await http.get(uri, headers: headers).timeout(const Duration(seconds: 20));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SongAnalysis.fromJson(data);
      }
    } catch (_) {
      // Try fallback below
    }

    // Fallback: unified analyze job endpoint containing result object
    try {
      final fallbackUri = Uri.parse('$effectiveUrl/analyze/$analysisId');
      final fallbackRes = await http.get(fallbackUri, headers: headers).timeout(const Duration(seconds: 20));
      if (fallbackRes.statusCode == 200) {
        final data = jsonDecode(fallbackRes.body) as Map<String, dynamic>;
        if (data['result'] != null) {
          return SongAnalysis.fromJson(data['result'] as Map<String, dynamic>);
        }
      }
    } catch (e) {
      throw Exception(_formatConnectionError(effectiveUrl, e));
    }

    throw Exception('Analysis result not ready or not found for: $analysisId from $effectiveUrl');
  }

  @override
  Future<SongAnalysis> transpose({
    required SongAnalysis currentAnalysis,
    required int semitones,
  }) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = {'Content-Type': 'application/json', ..._getHeaders()};

    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/${currentAnalysis.id}/transpose');
      final response = await http.post(
        uri,
        headers: headers,
        body: jsonEncode({'semitones': semitones}),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SongAnalysis.fromJson(data);
      }
    } catch (_) {
      // Offline fallback: use local transpose service
    }

    return TransposeService.transposeSong(currentAnalysis, semitones);
  }

  @override
  Future<SongAnalysis> editChord({
    required SongAnalysis currentAnalysis,
    required int chordIndex,
    required String root,
    required String quality,
    String? bass,
    String? display,
  }) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = {'Content-Type': 'application/json', ..._getHeaders()};
    final newDisplay = display ?? (bass != null && bass != root ? '$root$quality/$bass' : '$root$quality');

    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/${currentAnalysis.id}/edit');
      final response = await http.post(
        uri,
        headers: headers,
        body: jsonEncode({
          'chord_index': chordIndex,
          'new_root': root,
          'new_quality': quality,
          'new_bass': bass,
          'new_display': display,
        }),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SongAnalysis.fromJson(data);
      }
    } catch (_) {
      // Offline fallback: edit in-memory
    }

    // Apply local edit
    if (chordIndex >= 0 && chordIndex < currentAnalysis.chords.length) {
      final c = currentAnalysis.chords[chordIndex];
      c.root = root;
      c.quality = quality;
      c.bass = bass ?? root;
      c.display = newDisplay;

      for (final sec in currentAnalysis.sections) {
        for (final bar in sec.bars) {
          for (final bc in bar.chords) {
            if ((bc.startTime - c.startTime).abs() < 0.05) {
              bc.root = root;
              bc.quality = quality;
              bc.bass = bass ?? root;
              bc.display = newDisplay;
            }
          }
          bar.display = bar.chords.map((x) => x.display).join(' | ');
        }
      }
    }

    return currentAnalysis;
  }

  @override
  Future<SongAnalysis> renameSection({
    required SongAnalysis currentAnalysis,
    required String sectionId,
    required String newName,
  }) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = {'Content-Type': 'application/json', ..._getHeaders()};
    final cleanName = newName.trim().toUpperCase();

    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/${currentAnalysis.id}/rename-section');
      final response = await http.post(
        uri,
        headers: headers,
        body: jsonEncode({
          'section_id': sectionId,
          'new_name': cleanName,
        }),
      ).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SongAnalysis.fromJson(data);
      }
    } catch (_) {
      // Offline fallback: rename in-memory
    }

    for (final sec in currentAnalysis.sections) {
      if (sec.sectionId == sectionId) {
        sec.name = cleanName;
        break;
      }
    }

    return currentAnalysis;
  }

  @override
  Future<SongAnalysis> changeMeter({
    required SongAnalysis currentAnalysis,
    required int numerator,
    required int denominator,
    String? subgrouping,
  }) async {
    final effectiveUrl = await _getEffectiveBaseUrl();
    final headers = {'Content-Type': 'application/json', ..._getHeaders()};

    try {
      final uri = Uri.parse('$effectiveUrl/api/analysis/${currentAnalysis.id}/meter');
      final response = await http.post(
        uri,
        headers: headers,
        body: jsonEncode({
          'numerator': numerator,
          'denominator': denominator,
          'subgrouping': subgrouping,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        return SongAnalysis.fromJson(data);
      }
    } catch (_) {
      // Offline fallback
    }

    currentAnalysis.meter = MeterAnalysis(
      numerator: numerator,
      denominator: denominator,
      display: '$numerator/$denominator',
      confidence: currentAnalysis.meter.confidence,
      isEstimated: false,
      candidateScores: currentAnalysis.meter.candidateScores,
      downbeatConfidence: currentAnalysis.meter.downbeatConfidence,
      meterEvidence: currentAnalysis.meter.meterEvidence,
      subgrouping: subgrouping,
    );
    return currentAnalysis;
  }
}
