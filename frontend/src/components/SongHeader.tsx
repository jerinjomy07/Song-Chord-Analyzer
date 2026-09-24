import React, { useState } from 'react';
import { Music, Activity, Clock, Sliders, Cpu, RotateCcw, Edit2, Check, X, Loader2 } from 'lucide-react';
import type { SongAnalysis } from '../types';

interface SongHeaderProps {
  analysis: SongAnalysis;
  onReset: () => void;
  onRenameTitle?: (newTitle: string) => Promise<void> | void;
}

export const SongHeader: React.FC<SongHeaderProps> = ({ analysis, onReset, onRenameTitle }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [titleInput, setTitleInput] = useState(analysis.title);
  const [isSaving, setIsSaving] = useState(false);

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const remainingSecs = Math.floor(secs % 60);
    return `${mins}:${remainingSecs < 10 ? '0' : ''}${remainingSecs}`;
  };

  const handleStartEdit = () => {
    setTitleInput(analysis.title);
    setIsEditing(true);
  };

  const handleCancelEdit = () => {
    setTitleInput(analysis.title);
    setIsEditing(false);
  };

  const handleSaveTitle = async () => {
    const trimmed = titleInput.trim();
    if (!trimmed || trimmed === analysis.title) {
      setIsEditing(false);
      return;
    }

    if (onRenameTitle) {
      setIsSaving(true);
      try {
        await onRenameTitle(trimmed);
        setIsEditing(false);
      } catch (err) {
        console.error('Failed to rename song title:', err);
      } finally {
        setIsSaving(false);
      }
    } else {
      setIsEditing(false);
    }
  };

  return (
    <div className="w-full bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl mb-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Analysis Completed
            </span>
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Cpu size={12} />
              <span>{analysis.pipeline_metadata.device_used.toUpperCase()} Accelerated</span>
            </span>
          </div>

          {/* Song Title with Option to Rename */}
          {isEditing ? (
            <div className="flex items-center gap-2 mt-1">
              <input
                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleSaveTitle();
                  if (e.key === 'Escape') handleCancelEdit();
                }}
                autoFocus
                className="bg-slate-950 border border-indigo-500 rounded-xl px-3 py-1.5 text-xl sm:text-2xl font-extrabold text-white focus:outline-none max-w-lg w-full"
                placeholder="Song Title..."
              />
              <button
                onClick={handleSaveTitle}
                disabled={isSaving || !titleInput.trim()}
                className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white cursor-pointer transition-all shadow-md shadow-indigo-600/30 shrink-0"
                title="Save title"
              >
                {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              </button>
              <button
                onClick={handleCancelEdit}
                disabled={isSaving}
                className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 cursor-pointer transition-all shrink-0"
                title="Cancel"
              >
                <X size={16} />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2.5 group">
              <h1 className="text-2xl md:text-3xl font-extrabold text-white tracking-tight truncate" title={analysis.title}>
                {analysis.title}
              </h1>
              {onRenameTitle && (
                <button
                  onClick={handleStartEdit}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-all cursor-pointer opacity-70 group-hover:opacity-100 shrink-0"
                  title="Rename song title"
                >
                  <Edit2 size={16} />
                </button>
              )}
            </div>
          )}
        </div>

        <button
          onClick={onReset}
          className="self-start md:self-auto px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-all cursor-pointer shrink-0"
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
