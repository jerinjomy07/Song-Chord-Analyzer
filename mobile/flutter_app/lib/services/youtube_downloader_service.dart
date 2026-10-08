import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:youtube_explode_dart/youtube_explode_dart.dart';
import 'server_config_service.dart';

class YouTubeVideoMeta {
  final String id;
  final String title;
  final String author;
  final Duration? duration;
  final String thumbnailUrl;
  final String originalUrl;

  YouTubeVideoMeta({
    required this.id,
    required this.title,
    required this.author,
    this.duration,
    required this.thumbnailUrl,
    required this.originalUrl,
  });
}

class YouTubeDownloaderService {
  /// Extracts the 11-character video ID from various YouTube URL formats.
  static String? extractVideoId(String url) {
    final clean = url.trim();
    if (clean.isEmpty) return null;

    final regExp = RegExp(
      r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|v\/|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
      caseSensitive: false,
    );

    final match = regExp.firstMatch(clean);
    if (match != null && match.groupCount >= 1) {
      return match.group(1);
    }

    // Direct 11-character video ID
    if (RegExp(r'^[a-zA-Z0-9_-]{11}$').hasMatch(clean)) {
      return clean;
    }

    return null;
  }

  /// Gets the configured server base URL.
  static Future<String> _getServerBaseUrl() async {
    try {
      final config = ServerConfigService.instance;
      final activeUrl = await config.resolveActiveUrl();
      if (activeUrl.isNotEmpty) {
        return activeUrl.replaceAll(RegExp(r'/+$'), '');
      }
    } catch (_) {}
    return const String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');
  }

  static Map<String, String> _getHeaders({Map<String, String>? extra}) {
    final headers = <String, String>{
      'Content-Type': 'application/json',
    };
    final key = ServerConfigService.instance.config.apiKey.trim();
    if (key.isNotEmpty) {
      headers['X-API-Key'] = key;
    }
    if (extra != null) {
      headers.addAll(extra);
    }
    return headers;
  }

  /// Fetches video details without downloading the full audio stream.
  static Future<YouTubeVideoMeta> fetchVideoDetails(String url) async {
    final videoId = extractVideoId(url);
    if (videoId == null) {
      throw ArgumentError('Invalid or unsupported YouTube URL.');
    }

    // 1. Try server info endpoint first
    try {
      final baseUrl = await _getServerBaseUrl();
      final uri = Uri.parse('$baseUrl/api/sources/youtube/info');
      final res = await http.post(
        uri,
        headers: _getHeaders(),
        body: jsonEncode({'url': url}),
      ).timeout(const Duration(seconds: 8));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final durSec = (data['duration'] as num?)?.toInt() ?? 0;
        return YouTubeVideoMeta(
          id: (data['video_id'] as String?) ?? videoId,
          title: (data['title'] as String?) ?? 'YouTube Song',
          author: (data['channel'] as String?) ?? 'Unknown Artist',
          duration: durSec > 0 ? Duration(seconds: durSec) : null,
          thumbnailUrl: (data['thumbnail_url'] as String?) ?? 'https://img.youtube.com/vi/$videoId/hqdefault.jpg',
          originalUrl: url,
        );
      }
    } catch (_) {
      // Fallback to on-device YoutubeExplode
    }

    // 2. On-device YoutubeExplode fallback
    final yt = YoutubeExplode();
    try {
      final video = await yt.videos.get(videoId);
      return YouTubeVideoMeta(
        id: video.id.value,
        title: video.title,
        author: video.author,
        duration: video.duration,
        thumbnailUrl: video.thumbnails.highResUrl,
        originalUrl: url,
      );
    } finally {
      yt.close();
    }
  }

  /// Downloads audio (via server yt-dlp with on-device fallback) to local cache.
  static Future<File> downloadAudio(
    String url, {
    void Function(double progress, String status)? onProgress,
  }) async {
    final videoId = extractVideoId(url);
    if (videoId == null) {
      throw ArgumentError('Invalid or unsupported YouTube URL.');
    }

    final tempDir = await getTemporaryDirectory();
    final cacheDir = Directory('${tempDir.path}/youtube_cache');
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }

    // Check if cached MP3 or M4A already exists
    for (final ext in ['mp3', 'm4a', 'opus', 'webm']) {
      final cached = File('${cacheDir.path}/yt_${videoId}.$ext');
      if (await cached.exists() && await cached.length() > 1024) {
        onProgress?.call(1.0, 'Cached audio ready.');
        return cached;
      }
    }

    final targetFile = File('${cacheDir.path}/yt_${videoId}.mp3');

    // 1. Primary: Server-assisted fast extraction via yt-dlp
    try {
      final baseUrl = await _getServerBaseUrl();
      onProgress?.call(0.15, 'Requesting fast audio extraction from server...');

      final uri = Uri.parse('$baseUrl/api/sources/youtube/download');
      final res = await http.post(
        uri,
        headers: _getHeaders(),
        body: jsonEncode({'url': url}),
      ).timeout(const Duration(seconds: 60));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body) as Map<String, dynamic>;
        final downloadUrl = data['download_url'] as String?;
        if (downloadUrl != null && downloadUrl.isNotEmpty) {
          onProgress?.call(0.40, 'Audio extracted on server. Transferring to device...');
          final audioUri = Uri.parse('$baseUrl$downloadUrl');

          final client = http.Client();
          try {
            final request = http.Request('GET', audioUri);
            final key = ServerConfigService.instance.config.apiKey.trim();
            if (key.isNotEmpty) {
              request.headers['X-API-Key'] = key;
            }
            final streamedRes = await client.send(request).timeout(const Duration(seconds: 30));

            if (streamedRes.statusCode == 200) {
              final totalBytes = streamedRes.contentLength ?? 0;
              var downloadedBytes = 0;
              final sink = targetFile.openWrite();
              try {
                await for (final chunk in streamedRes.stream.timeout(
                  const Duration(seconds: 30),
                  onTimeout: (sink) => sink.addError(TimeoutException('Transfer stalled')),
                )) {
                  downloadedBytes += chunk.length;
                  sink.add(chunk);

                  if (totalBytes > 0) {
                    final progress = 0.40 + 0.60 * (downloadedBytes / totalBytes);
                    final mbDone = (downloadedBytes / (1024 * 1024)).toStringAsFixed(1);
                    final mbTotal = (totalBytes / (1024 * 1024)).toStringAsFixed(1);
                    onProgress?.call(progress.clamp(0.0, 1.0), 'Transferring audio: $mbDone / $mbTotal MB');
                  }
                }
                await sink.flush();
              } finally {
                await sink.close();
              }

              if (await targetFile.exists() && await targetFile.length() > 1024) {
                onProgress?.call(1.0, 'Audio ready for analysis.');
                return targetFile;
              }
            }
          } finally {
            client.close();
          }
        }
      }
    } catch (serverErr) {
      // Server extraction failed or server offline; try on-device fallback
    }

    // 2. Fallback: On-device extraction with YoutubeExplode + timeout guard
    final yt = YoutubeExplode();
    File? localFallbackFile;
    try {
      onProgress?.call(0.15, 'Fetching YouTube stream manifest...');
      final manifest = await yt.videos.streamsClient.getManifest(videoId).timeout(
        const Duration(seconds: 15),
        onTimeout: () => throw TimeoutException('Manifest request timed out.'),
      );

      AudioStreamInfo? selectedStream;
      final mp4AudioStreams = manifest.audioOnly.where((s) => s.container.name.toLowerCase() == 'mp4').toList();
      if (mp4AudioStreams.isNotEmpty) {
        selectedStream = mp4AudioStreams.withHighestBitrate();
      } else {
        selectedStream = manifest.audioOnly.withHighestBitrate();
      }

      final ext = selectedStream.container.name.toLowerCase() == 'mp4' ? 'm4a' : selectedStream.container.name;
      localFallbackFile = File('${cacheDir.path}/yt_${videoId}.$ext');

      onProgress?.call(0.20, 'Downloading direct audio stream (${(selectedStream.size.totalMegaBytes).toStringAsFixed(1)} MB)...');
      final audioStream = yt.videos.streamsClient.get(selectedStream);
      final fileStream = localFallbackFile.openWrite();

      final totalBytes = selectedStream.size.totalBytes;
      int downloadedBytes = 0;

      try {
        await for (final chunk in audioStream.timeout(
          const Duration(seconds: 20),
          onTimeout: (sink) => sink.addError(TimeoutException('YouTube direct stream stalled by network.')),
        )) {
          downloadedBytes += chunk.length;
          fileStream.add(chunk);

          if (totalBytes > 0) {
            final progress = 0.20 + 0.80 * (downloadedBytes / totalBytes);
            final mbDone = (downloadedBytes / (1024 * 1024)).toStringAsFixed(1);
            final mbTotal = (totalBytes / (1024 * 1024)).toStringAsFixed(1);
            onProgress?.call(progress.clamp(0.0, 1.0), 'Downloading: $mbDone / $mbTotal MB');
          }
        }
        await fileStream.flush();
      } finally {
        await fileStream.close();
      }

      if (await localFallbackFile.exists() && await localFallbackFile.length() > 1024) {
        onProgress?.call(1.0, 'Audio ready for analysis.');
        return localFallbackFile;
      }
      throw Exception('Downloaded audio file is invalid.');
    } catch (e) {
      if (localFallbackFile != null && await localFallbackFile.exists()) {
        try {
          await localFallbackFile.delete();
        } catch (_) {}
      }
      throw Exception(
        'Could not retrieve YouTube audio stream.\n'
        'Please ensure your laptop Chord Analyzer Server is running and connected in Settings.',
      );
    } finally {
      yt.close();
    }
  }
}
