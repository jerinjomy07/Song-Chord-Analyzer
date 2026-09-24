import React from 'react';
import type { HistorySong } from '../types';
import { Copy, FolderOpen, RotateCcw, X, Music, Activity, Clock } from 'lucide-react';

interface DuplicateModalProps {
  existingSong: HistorySong;
  fileName: string;
  onOpenExisting: (songId: string) => void;
  onAnalyzeAgain: () => void;
  onCancel: () => void;
}

export const DuplicateModal: React.FC<DuplicateModalProps> = ({
  existingSong,
  fileName,
  onOpenExisting,
  onAnalyzeAgain,
  onCancel,
}) => {
  const formatDuration = (secs: number) => {
    if (!secs) return '0:00';
    const mins = Math.floor(secs / 60);
    const rem = Math.floor(secs % 60);
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-6 max-w-lg w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center border border-indigo-500/20">
              <Copy size={20} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">Song Already in History</h3>
              <p className="text-xs text-slate-400">Content match found in your library</p>
            </div>
          </div>
          <button
            onClick={onCancel}
            className="text-slate-400 hover:text-slate-200 p-1 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        <p className="text-xs text-slate-300 leading-relaxed mb-4">
          The file <span className="font-semibold text-white">"{fileName}"</span> has identical audio content to a song you've already analyzed:
        </p>

        {/* Existing Song Summary Card */}
        <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-bold text-white truncate">{existingSong.title}</h4>
            <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              {existingSong.format || 'AUDIO'}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-2 text-xs py-2 border-y border-slate-800/80 my-2">
            <div className="flex items-center gap-1.5">
              <Music size={13} className="text-indigo-400" />
              <span className="text-slate-300 font-semibold">{existingSong.key_display || 'Key —'}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Activity size={13} className="text-amber-400" />
              <span className="text-slate-300 font-semibold">{existingSong.bpm ? `${existingSong.bpm} BPM` : 'BPM —'}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock size={13} className="text-cyan-400" />
              <span className="text-slate-300 font-semibold">{formatDuration(existingSong.duration)}</span>
            </div>
          </div>

          <p className="text-[11px] text-slate-500">
            Previously analyzed on {formatDate(existingSong.created_at)}
            {existingSong.edit_count > 0 && ` • Contains ${existingSong.edit_count} saved edits`}
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-end gap-2.5">
          <button
            onClick={onCancel}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-800 cursor-pointer transition-colors order-3 sm:order-1"
          >
            Cancel
          </button>

          <button
            onClick={onAnalyzeAgain}
            className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all border border-slate-700 order-2"
          >
            <RotateCcw size={14} className="text-amber-400" />
            <span>Analyze Again</span>
          </button>

          <button
            onClick={() => onOpenExisting(existingSong.id)}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg shadow-indigo-600/30 transition-all order-1 sm:order-3"
          >
            <FolderOpen size={14} />
            <span>Open Existing (Instant)</span>
          </button>
        </div>
      </div>
    </div>
  );
};
