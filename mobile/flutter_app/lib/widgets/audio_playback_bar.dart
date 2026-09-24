import 'package:flutter/material.dart';
import 'package:audioplayers/audioplayers.dart';
import '../services/audio_player_service.dart';

class AudioPlaybackBar extends StatelessWidget {
  final AudioPlayerService playerService;
  final bool autoScrollEnabled;
  final ValueChanged<bool> onAutoScrollChanged;

  const AudioPlaybackBar({
    super.key,
    required this.playerService,
    required this.autoScrollEnabled,
    required this.onAutoScrollChanged,
  });

  String _formatDuration(Duration d) {
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.grey.shade900,
        boxShadow: const [
          BoxShadow(
            color: Colors.black26,
            blurRadius: 10,
            offset: Offset(0, -3),
          ),
        ],
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Timeline scrubber & times
            StreamBuilder<Duration>(
              stream: playerService.positionStream,
              initialData: playerService.currentPosition,
              builder: (context, snapshot) {
                final pos = snapshot.data ?? Duration.zero;
                final total = playerService.totalDuration;
                final maxSec = total.inMilliseconds > 0 ? total.inMilliseconds.toDouble() : 1.0;
                final curSec = pos.inMilliseconds.toDouble().clamp(0.0, maxSec);

                return Row(
                  children: [
                    Text(
                      _formatDuration(pos),
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                    Expanded(
                      child: SliderTheme(
                        data: SliderTheme.of(context).copyWith(
                          trackHeight: 3,
                          thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                          activeTrackColor: Colors.indigoAccent,
                          inactiveTrackColor: Colors.white24,
                          thumbColor: Colors.indigoAccent,
                        ),
                        child: Slider(
                          value: curSec,
                          max: maxSec,
                          onChanged: (val) {
                            playerService.seek(Duration(milliseconds: val.toInt()));
                          },
                        ),
                      ),
                    ),
                    Text(
                      _formatDuration(total),
                      style: const TextStyle(color: Colors.white70, fontSize: 12),
                    ),
                  ],
                );
              },
            ),

            // Controls row
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Auto Scroll toggle
                Row(
                  children: [
                    Icon(
                      autoScrollEnabled ? Icons.sync : Icons.sync_disabled,
                      size: 16,
                      color: autoScrollEnabled ? Colors.indigoAccent : Colors.grey,
                    ),
                    const SizedBox(width: 4),
                    Text(
                      'Auto-Scroll',
                      style: TextStyle(
                        fontSize: 12,
                        color: autoScrollEnabled ? Colors.white : Colors.grey,
                      ),
                    ),
                    Transform.scale(
                      scale: 0.7,
                      child: Switch(
                        value: autoScrollEnabled,
                        activeColor: Colors.indigoAccent,
                        onChanged: onAutoScrollChanged,
                      ),
                    ),
                  ],
                ),

                // Play / Pause button
                StreamBuilder<PlayerState>(
                  stream: playerService.stateStream,
                  initialData: playerService.playerState,
                  builder: (context, snapshot) {
                    final isPlaying = snapshot.data == PlayerState.playing;

                    return Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        IconButton(
                          icon: const Icon(Icons.replay_10, color: Colors.white70),
                          onPressed: () {
                            final newPos = playerService.currentPosition - const Duration(seconds: 10);
                            playerService.seek(newPos < Duration.zero ? Duration.zero : newPos);
                          },
                        ),
                        CircleAvatar(
                          backgroundColor: Colors.indigoAccent,
                          radius: 22,
                          child: IconButton(
                            icon: Icon(
                              isPlaying ? Icons.pause : Icons.play_arrow,
                              color: Colors.white,
                              size: 26,
                            ),
                            onPressed: () {
                              if (isPlaying) {
                                playerService.pause();
                              } else {
                                playerService.play();
                              }
                            },
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.forward_10, color: Colors.white70),
                          onPressed: () {
                            final newPos = playerService.currentPosition + const Duration(seconds: 10);
                            playerService.seek(newPos);
                          },
                        ),
                      ],
                    );
                  },
                ),

                const SizedBox(width: 40), // Spacer balancing left toggle
              ],
            ),
          ],
        ),
      ),
    );
  }
}
