import React from 'react';
import { Music, Activity, Clock, Sliders, Cpu, RotateCcw } from 'lucide-react';
import type { SongAnalysis } from '../types';

interface SongHeaderProps {
  analysis: SongAnalysis;
  onReset: () => void;
}

export const SongHeader: React.FC<SongHeaderProps> = ({ analysis, onReset }) => {
  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs < 10 ? '0' : ''}${remainingSecs}`;
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Analysis Completed
            </span>
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Cpu size={12} />
              <span>{analysis.pipeline_metadata.device_used.toUpperCase()} Accelerated</span>
            </span>
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight">
            {analysis.title}
          </h1>
        </div>

        <button
          onClick={onReset}
          className="self-start md:self-auto px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-all cursor-pointer"
        >
          <RotateCcw size={16} />
          <span>New Song</span>
        </button>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6">
        {/* Key */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 flex items-center justify-center text-indigo-400">
            <Music size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Key</p>
            <p className="text-base font-bold text-slate-100">{analysis.key.display}</p>
          </div>
        </div>

        {/* Tempo */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
            <Activity size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Tempo</p>
            <p className="text-base font-bold text-slate-100">
              {analysis.tempo.bpm} <span className="text-xs font-normal text-slate-400">BPM</span>
            </p>
          </div>
        </div>

        {/* Time Signature */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <Sliders size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Meter</p>
            <p className="text-base font-bold text-slate-100">{analysis.meter.display}</p>
          </div>
        </div>

        {/* Duration */}
        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400">
            <Clock size={20} />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Duration</p>
            <p className="text-base font-bold text-slate-100">{formatTime(analysis.metadata.duration)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};
