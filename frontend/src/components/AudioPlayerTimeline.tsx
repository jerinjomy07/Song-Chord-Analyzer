import React, { useRef } from 'react';
import { Play, Pause } from 'lucide-react';
import type { SongAnalysis, ChordPrediction } from '../types';

interface AudioPlayerTimelineProps {
  analysis: SongAnalysis;
  currentTime: number;
  isPlaying: boolean;
  onPlayPause: () => void;
  onSeek: (timeSec: number) => void;
  onSelectChord: (chord: ChordPrediction, index: number) => void;
}

export const AudioPlayerTimeline: React.FC<AudioPlayerTimelineProps> = ({
  analysis,
  currentTime,
  isPlaying,
  onPlayPause,
  onSeek,
  onSelectChord,
}) => {
  const duration = analysis.metadata.duration || 1;
  const progressPercent = Math.min(100, Math.max(0, (currentTime / duration) * 100));
  const timelineRef = useRef<HTMLDivElement>(null);

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

  // Find currently active chord
  const activeChord = analysis.chords.find(
    c => c.start_time <= currentTime && c.end_time >= currentTime
  );

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-xl mb-6">
      {/* Player Header Controls */}
      <div className="flex items-center justify-between gap-4 mb-4">
        <div className="flex items-center gap-3">
          <button
            onClick={onPlayPause}
            className="w-11 h-11 rounded-full bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white flex items-center justify-center shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
          >
            {isPlaying ? <Pause size={20} /> : <Play size={20} className="ml-0.5" />}
          </button>

          <div>
            <div className="flex items-baseline gap-2">
              <span className="font-mono text-sm font-semibold text-slate-200">
                {formatTime(currentTime)}
              </span>
              <span className="text-xs text-slate-500 font-mono">
                / {formatTime(duration)}
              </span>
            </div>
            <p className="text-xs text-slate-400">
              {activeChord ? `Active: ${activeChord.display}` : 'Audio Player & Timeline'}
            </p>
          </div>
        </div>

        {/* Current Chord Callout */}
        {activeChord && activeChord.display !== 'N' && (
          <div className="px-4 py-1.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-center">
            <span className="text-xs text-indigo-400 font-medium block">Current Chord</span>
            <span className="text-lg font-black text-white">{activeChord.display}</span>
          </div>
        )}
      </div>

      {/* Sections Track */}
      <div className="relative h-6 w-full bg-slate-950 rounded-t-lg overflow-hidden flex border-b border-slate-800 text-[10px] font-bold text-slate-400 select-none">
        {analysis.sections.map((sec, idx) => {
          const leftPct = (sec.start_time / duration) * 100;
          const widthPct = ((sec.end_time - sec.start_time) / duration) * 100;
          return (
            <div
              key={sec.section_id || idx}
              style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
              className="absolute top-0 bottom-0 border-r border-slate-800/80 px-1.5 flex items-center truncate bg-slate-900/50 hover:bg-slate-800/80 cursor-pointer transition-colors"
              onClick={() => onSeek(sec.start_time)}
              title={`${sec.name} (${formatTime(sec.start_time)})`}
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
                  ? 'bg-indigo-600/40 text-white' 
                  : chord.display === 'N' 
                  ? 'bg-slate-900/20 text-slate-600' 
                  : 'bg-slate-900/40 text-slate-300 hover:bg-slate-800'
              }`}
              onClick={(e) => {
                e.stopPropagation();
                onSeek(chord.start_time);
                onSelectChord(chord, idx);
              }}
              title={`${chord.display} at ${formatTime(chord.start_time)} (Click to play/edit)`}
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
          className="absolute top-0 bottom-0 w-0.5 bg-red-500 shadow-md shadow-red-500/50 pointer-events-none"
          style={{ left: `${progressPercent}%` }}
        />
      </div>
    </div>
  );
};
