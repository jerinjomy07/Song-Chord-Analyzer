import React, { useState } from 'react';
import { Music, Activity, Clock, Sliders, Cpu, RotateCcw, Edit2, Check, X, Loader2, ExternalLink } from 'lucide-react';
import type { SongAnalysis } from '../types';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 14, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface SongHeaderProps {
  analysis: SongAnalysis;
  onReset: () => void;
  onRenameTitle?: (newTitle: string) => Promise<void> | void;
  onReanalyze?: (songId: string) => void;
}

export const SongHeader: React.FC<SongHeaderProps> = ({ analysis, onReset, onRenameTitle, onReanalyze }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [titleInput, setTitleInput] = useState(analysis.title);
  const [isSaving, setIsSaving] = useState(false);
  const [showReanalyzeConfirm, setShowReanalyzeConfirm] = useState(false);

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
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              Analysis Completed
            </span>
            <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <Cpu size={12} />
              <span>{analysis.pipeline_metadata.device_used.toUpperCase()} Accelerated</span>
            </span>
            {analysis.source_metadata?.type === 'youtube_reference' && (
              <a
                href={analysis.source_metadata.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-300 border border-red-500/20 hover:border-red-500/40 hover:bg-red-500/20 transition-all cursor-pointer"
                title="View referenced video on YouTube"
              >
                <YoutubeIcon size={12} className="text-red-400" />
                <span>YouTube Ref</span>
                <ExternalLink size={10} className="text-red-400" />
              </a>
            )}
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

        <div className="flex items-center gap-2.5 self-start md:self-auto shrink-0 flex-wrap">
          {onReanalyze && (
            <button
              onClick={() => setShowReanalyzeConfirm(true)}
              className="px-3.5 py-2 rounded-xl bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:border-amber-500/50 text-sm font-semibold flex items-center gap-2 transition-all cursor-pointer shadow-sm shadow-amber-500/10"
              title="Re-analyze this song using the latest music analysis engine"
            >
              <RotateCcw size={15} className="text-amber-400" />
              <span>Re-analyze</span>
            </button>
          )}

          <button
            onClick={onReset}
            className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center gap-2 transition-all cursor-pointer"
          >
            <Music size={16} />
            <span>New Song</span>
          </button>
        </div>
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

      {/* RE-ANALYZE CONFIRMATION MODAL */}
      {showReanalyzeConfirm && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-amber-500/30 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center border border-amber-500/20">
                <RotateCcw size={20} />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Re-analyze Song?</h3>
                <p className="text-xs text-slate-400">Re-run audio through latest analysis engine</p>
              </div>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mb-6">
              This will re-run harmonic tempo estimation, meter & downbeat detection, and BTC chord recognition on <span className="font-semibold text-white">"{analysis.title}"</span> using its stored audio file. Any manual chord edits will be refreshed.
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowReanalyzeConfirm(false)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  setShowReanalyzeConfirm(false);
                  if (onReanalyze) onReanalyze(analysis.id);
                }}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold transition-all shadow-lg shadow-amber-600/30 flex items-center gap-1.5 cursor-pointer"
              >
                <RotateCcw size={14} />
                <span>Re-analyze Now</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
