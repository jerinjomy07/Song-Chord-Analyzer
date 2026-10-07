import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'services/analysis_engine.dart';
import 'services/dev_http_analysis_engine.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final prefs = await SharedPreferences.getInstance();

  const envBaseUrl = String.fromEnvironment('API_BASE_URL', defaultValue: '');
  final defaultUrl = envBaseUrl.isNotEmpty ? envBaseUrl : 'http://10.0.2.2:8000';
  final devUrl = prefs.getString('dev_server_url') ?? defaultUrl;

  // Authoritative MIR Engine: FastAPI Server Analysis Engine
  final AnalysisEngine engine = DevHttpAnalysisEngine(baseUrl: devUrl);

  runApp(SongChordAnalyzerApp(analysisEngine: engine));
}

class SongChordAnalyzerApp extends StatelessWidget {
  final AnalysisEngine analysisEngine;

  const SongChordAnalyzerApp({
    super.key,
    required this.analysisEngine,
  });

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Song Chord Analyzer',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: Colors.indigo,
          primary: Colors.indigo,
          secondary: Colors.amber.shade700,
          surface: Colors.grey.shade50,
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.white,
          foregroundColor: Colors.indigo,
          elevation: 1,
          centerTitle: false,
        ),
      ),
      home: HomeScreen(analysisEngine: analysisEngine),
    );
  }
}
