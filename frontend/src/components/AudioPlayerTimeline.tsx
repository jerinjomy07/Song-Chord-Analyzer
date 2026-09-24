import React, { useRef, useState } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';
import type { SongAnalysis, ChordPrediction, Bar, MusicalSection } from '../types';

interface AudioPlayerTimelineProps {
  analysis: SongAnalysis;
  currentTime: number;
  isPlaying: boolean;
  onPlayPause: () => void;
  onSeek: (timeSec: number) => void;
  onSelectChord: (chord: ChordPrediction, index: number) => void;
  volume?: number;
  onVolumeChange?: (val: number) => void;
}

export const AudioPlayerTimeline: React.FC<AudioPlayerTimelineProps> = ({
  analysis,
  currentTime,
  isPlaying,
  onPlayPause,
  onSeek,
  onSelectChord,
  volume = 1,
  onVolumeChange,
}) => {
  const duration = analysis.metadata.duration || 1;
  const progressPercent = Math.min(100, Math.max(0, (currentTime / duration) * 100));
  const timelineRef = useRef<HTMLDivElement>(null);
  const [localVolume, setLocalVolume] = useState<number>(volume);
  const [isMuted, setIsMuted] = useState(false);

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const rem = Math.floor(secs % 60);
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  const handleTimelineClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!timelineRef.current) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const pct = Math.max(0, Math.min(1, clickX / rect.width));
    onSeek(pct * duration);
  };

  // Find currently active section
  const activeSection: MusicalSection | undefined = analysis.sections.find(
    s => currentTime >= s.start_time && currentTime <= s.end_time
  );

  // Find currently active bar
  let activeBar: Bar | null = null;
  if (activeSection) {
    activeBar = activeSection.bars.find(b => currentTime >= b.start_time && currentTime <= b.end_time) || null;
  }
  if (!activeBar) {
    for (const sec of analysis.sections) {
      const b = sec.bars.find(b => currentTime >= b.start_time && currentTime <= b.end_time);
      if (b) {
        activeBar = b;
        break;
      }
    }
  }

  // Find currently active chord
  const activeChord = analysis.chords.find(
    c => c.start_time <= currentTime && c.end_time >= currentTime
  );

  const handleVolumeSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setLocalVolume(val);
    if (isMuted && val > 0) setIsMuted(false);
    if (onVolumeChange) onVolumeChange(val);
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (onVolumeChange) onVolumeChange(nextMuted ? 0 : localVolume);
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl mb-6">
      {/* Player Header Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        {/* Play/Pause & Timing */}
        <div className="flex items-center gap-3">
          <button
            onClick={onPlayPause}
            className="w-12 h-12 rounded-full bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white flex items-center justify-center shadow-lg shadow-indigo-600/30 transition-all cursor-pointer shrink-0"
            title={isPlaying ? "Pause playback" : "Start playback"}
          >
            {isPlaying ? <Pause size={22} /> : <Play size={22} className="ml-0.5" />}
          </button>

          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-base font-bold text-white">
                {formatTime(currentTime)}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                / {formatTime(duration)}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {isPlaying ? 'Playing audio...' : 'Paused'}
            </p>
          </div>

          {/* Volume Control */}
          <div className="flex items-center gap-1.5 ml-3 pl-3 border-l border-slate-800">
            <button
              onClick={toggleMute}
              className="text-slate-400 hover:text-slate-200 p-1 cursor-pointer transition-colors"
              title={isMuted ? "Unmute" : "Mute"}
            >
              {isMuted || localVolume === 0 ? <VolumeX size={16} /> : <Volume2 size={16} />}
            </button>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={isMuted ? 0 : localVolume}
              onChange={handleVolumeSlider}
              className="w-16 sm:w-20 h-1 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              title={`Volume: ${Math.round((isMuted ? 0 : localVolume) * 100)}%`}
            />
          </div>
        </div>

        {/* Live Musical Indicators: Current Section, Bar, Chord */}
        <div className="flex items-center gap-2 self-start md:self-auto flex-wrap">
          {/* Section Indicator */}
          <div className="px-3 py-1.5 rounded-xl bg-slate-950/70 border border-slate-800 text-center min-w-[90px]">
            <span className="text-[9px] text-slate-400 font-semibold tracking-wider uppercase block">CURRENT SECTION</span>
            <span className="text-xs font-bold text-indigo-300 uppercase truncate max-w-[120px] block">
              {activeSection ? activeSection.name : '—'}
            </span>
          </div>

          {/* Bar Indicator */}
          <div className="px-3 py-1.5 rounded-xl bg-slate-950/70 border border-slate-800 text-center min-w-[75px]">
            <span className="text-[9px] text-slate-400 font-semibold tracking-wider uppercase block">CURRENT BAR</span>
            <span className="text-xs font-bold text-amber-400 font-mono block">
              {activeBar ? `Bar ${activeBar.bar_number}` : '—'}
            </span>
          </div>

          {/* Active Chord Indicator */}
          <div className="px-4 py-1.5 rounded-xl bg-amber-400/15 border border-amber-400/40 text-center min-w-[85px]">
            <span className="text-[9px] text-amber-300 font-semibold tracking-wider uppercase block">CURRENT CHORD</span>
            <span className="text-base font-black text-amber-300 block">
              {activeChord && activeChord.display !== 'N' ? activeChord.display : '—'}
            </span>
          </div>
        </div>
      </div>

      {/* Sections Track */}
      <div className="relative h-6 w-full bg-slate-950 rounded-t-lg overflow-hidden flex border-b border-slate-800 text-[10px] font-bold text-slate-400 select-none">
        {analysis.sections.map((sec, idx) => {
          const leftPct = (sec.start_time / duration) * 100;
          const widthPct = ((sec.end_time - sec.start_time) / duration) * 100;
          const isCurrentSec = sec === activeSection;

          return (
            <div
              key={sec.section_id || idx}
              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
              className={`absolute top-0 bottom-0 border-r border-slate-800/80 px-1.5 flex items-center truncate cursor-pointer transition-colors ${
                isCurrentSec ? 'bg-indigo-900/60 text-indigo-200' : 'bg-slate-900/50 hover:bg-slate-800/80'
              }`}
              onClick={() => onSeek(sec.start_time)}
              title={`${sec.name} (${formatTime(sec.start_time)} - click to jump)`}
            >
              <span className="truncate">{sec.name}</span>
            </div>
          );
        })}
      </div>

      {/* Interactive Timeline & Waveform Scrubber */}
      <div
        ref={timelineRef}
        onClick={handleTimelineClick}
        className="relative h-12 w-full bg-slate-950 rounded-b-lg overflow-hidden cursor-pointer select-none group"
      >
        {/* Chord Blocks Track */}
        {analysis.chords.map((chord, idx) => {
          const leftPct = (chord.start_time / duration) * 100;
          const widthPct = Math.max(0.5, (chord.duration / duration) * 100);
          const isCurrent = chord === activeChord;

          return (
            <div
              key={idx}
              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
              className={`absolute top-0 bottom-0 border-r border-slate-800/60 flex items-center justify-center text-[10px] font-bold transition-colors ${
                isCurrent 
                  ? 'bg-amber-400 text-slate-950 font-black shadow-md' 
                  : chord.display === 'N' 
                  ? 'bg-slate-900/20 text-slate-600' 
                  : 'bg-slate-900/40 text-slate-300 hover:bg-slate-800'
              }`}
              onClick={(e) => {
                e.stopPropagation();
                onSeek(chord.start_time);
                onSelectChord(chord, idx);
              }}
              title={`${chord.display} at ${formatTime(chord.start_time)} (Click to jump)`}
            >
              {widthPct > 2 && (
                <span className="truncate px-0.5">{chord.display}</span>
              )}
            </div>
          );
        })}

        {/* Playhead Progress Bar */}
        <div
          className="absolute top-0 bottom-0 left-0 bg-indigo-500/20 pointer-events-none"
          style={{ width: `${progressPercent}%` }}
        />

        {/* Playhead Needle */}
        <div
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-md shadow-red-500/50 pointer-events-none z-10"
          style={{ left: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
};
