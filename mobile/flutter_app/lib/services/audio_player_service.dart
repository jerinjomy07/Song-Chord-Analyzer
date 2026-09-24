import 'dart:async';
import 'package:audioplayers/audioplayers.dart';
import '../models/song_analysis.dart';
import '../models/chord_prediction.dart';
import '../models/bar.dart';

class AudioPlayerService {
  final AudioPlayer _player = AudioPlayer();
  
  Duration _currentPosition = Duration.zero;
  Duration _totalDuration = Duration.zero;
  PlayerState _playerState = PlayerState.stopped;

  final StreamController<Duration> _positionController = StreamController<Duration>.broadcast();
  final StreamController<PlayerState> _stateController = StreamController<PlayerState>.broadcast();
  final StreamController<int> _activeBarController = StreamController<int>.broadcast();
  final StreamController<ChordPrediction?> _activeChordController = StreamController<ChordPrediction?>.broadcast();

  Stream<Duration> get positionStream => _positionController.stream;
  Stream<PlayerState> get stateStream => _stateController.stream;
  Stream<int> get activeBarStream => _activeBarController.stream;
  Stream<ChordPrediction?> get activeChordStream => _activeChordController.stream;

  Duration get currentPosition => _currentPosition;
  Duration get totalDuration => _totalDuration;
  PlayerState get playerState => _playerState;
  bool get isPlaying => _playerState == PlayerState.playing;

  SongAnalysis? _activeSong;
  int _lastActiveBar = -1;

  AudioPlayerService() {
    _player.onPositionChanged.listen((pos) {
      _currentPosition = pos;
      _positionController.add(pos);
      _syncPlayback(pos.inMilliseconds / 1000.0);
    });

    _player.onDurationChanged.listen((dur) {
      _totalDuration = dur;
    });

    _player.onPlayerStateChanged.listen((state) {
      _playerState = state;
      _stateController.add(state);
    });
  }

  void setActiveSong(SongAnalysis song) {
    _activeSong = song;
    _lastActiveBar = -1;
  }

  Future<void> loadAudio(String pathOrUrl, {bool isLocal = true}) async {
    if (isLocal) {
      await _player.setSource(DeviceFileSource(pathOrUrl));
    } else {
      await _player.setSource(UrlSource(pathOrUrl));
    }
  }

  Future<void> play() async {
    await _player.resume();
  }

  Future<void> pause() async {
    await _player.pause();
  }

  Future<void> stop() async {
    await _player.stop();
    _currentPosition = Duration.zero;
    _positionController.add(Duration.zero);
  }

  Future<void> seek(Duration position) async {
    await _player.seek(position);
  }

  void _syncPlayback(double currentTimeSeconds) {
    if (_activeSong == null) return;

    // Find active chord
    ChordPrediction? currentChord;
    for (final chord in _activeSong!.chords) {
      if (currentTimeSeconds >= chord.startTime && currentTimeSeconds < chord.endTime) {
        currentChord = chord;
        break;
      }
    }
    _activeChordController.add(currentChord);

    // Find active bar
    int currentBar = -1;
    for (final sec in _activeSong!.sections) {
      for (final bar in sec.bars) {
        if (currentTimeSeconds >= bar.startTime && currentTimeSeconds < bar.endTime) {
          currentBar = bar.barNumber;
          break;
        }
      }
      if (currentBar != -1) break;
    }

    if (currentBar != -1 && currentBar != _lastActiveBar) {
      _lastActiveBar = currentBar;
      _activeBarController.add(currentBar);
    }
  }

  void dispose() {
    _player.dispose();
    _positionController.close();
    _stateController.close();
    _activeBarController.close();
    _activeChordController.close();
  }
}
