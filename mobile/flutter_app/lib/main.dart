import 'package:flutter/material.dart';
import 'services/analysis_engine.dart';
import 'services/dev_http_analysis_engine.dart';
import 'services/server_config_service.dart';
import 'screens/home_screen.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final configService = ServerConfigService.instance;
  await configService.init();

  // Authoritative MIR Engine: FastAPI Server Analysis Engine with dual-mode support
  final AnalysisEngine engine = DevHttpAnalysisEngine(configService: configService);

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
