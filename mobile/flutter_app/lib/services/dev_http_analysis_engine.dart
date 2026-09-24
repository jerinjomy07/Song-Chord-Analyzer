import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'analysis_engine.dart';
import '../models/song_analysis.dart';
import '../models/analysis_status.dart';

class DevHttpAnalysisEngine implements AnalysisEngine {
  String baseUrl;

  DevHttpAnalysisEngine({
    this.baseUrl = 'http://10.0.2.2:8000', // Default Android emulator host loopback
  });

  void updateBaseUrl(String newUrl) {
    baseUrl = newUrl.replaceAll(RegExp(r'/+$'), '');
  }

  @override
  Future<String> startAnalysis({
    required File audioFile,
    required String songTitle,
  }) async {
    final uri = Uri.parse('$baseUrl/api/analyze');
    final request = http.MultipartRequest('POST', uri);
    request.fields['song_title'] = songTitle;
    request.files.add(await http.MultipartFile.fromPath(
      'file',
      audioFile.path,
      filename: audioFile.path.split(Platform.pathSeparator).last,
    ));

    final streamedResponse = await request.send();
    final response = await http.Response.fromStream(streamedResponse);

    if (response.statusCode != 200) {
      throw Exception('Failed to start analysis: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return data['analysis_id'] as String;
  }

  @override
  Future<AnalysisStatus> getStatus(String analysisId) async {
    final uri = Uri.parse('$baseUrl/api/analysis/$analysisId/status');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('Failed to get analysis status: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return AnalysisStatus.fromJson(data);
  }

  @override
  Future<SongAnalysis> getResult(String analysisId) async {
    final uri = Uri.parse('$baseUrl/api/analysis/$analysisId');
    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw Exception('Failed to get analysis result: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return SongAnalysis.fromJson(data);
  }

  @override
  Future<SongAnalysis> transpose({
    required SongAnalysis currentAnalysis,
    required int semitones,
  }) async {
    final uri = Uri.parse('$baseUrl/api/analysis/${currentAnalysis.id}/transpose');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'semitones': semitones}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to transpose: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return SongAnalysis.fromJson(data);
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
    final uri = Uri.parse('$baseUrl/api/analysis/${currentAnalysis.id}/chord');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'chord_index': chordIndex,
        'new_root': root,
        'new_quality': quality,
        'new_bass': bass,
        'new_display': display,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to edit chord: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return SongAnalysis.fromJson(data);
  }

  @override
  Future<SongAnalysis> renameSection({
    required SongAnalysis currentAnalysis,
    required String sectionId,
    required String newName,
  }) async {
    final uri = Uri.parse('$baseUrl/api/analysis/${currentAnalysis.id}/section');
    final response = await http.post(
      uri,
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'section_id': sectionId,
        'new_name': newName,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to rename section: ${response.body}');
    }

    final data = jsonDecode(response.body) as Map<String, dynamic>;
    return SongAnalysis.fromJson(data);
  }
}
