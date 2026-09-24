import React from 'react';
import { ArrowUp, ArrowDown, RotateCcw } from 'lucide-react';

interface TransposerToolbarProps {
  currentOffset: number;
  currentKey: string;
  onTranspose: (semitones: number) => void;
  onReset: () => void;
  isTransposing: boolean;
}

export const TransposerToolbar: React.FC<TransposerToolbarProps> = ({
  currentOffset,
  currentKey,
  onTranspose,
  onReset,
  isTransposing
}) => {
  return (
    <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl p-2 px-3">
      <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider mr-1">
        Transpose
      </span>

      <button
        onClick={() => onTranspose(-1)}
        disabled={isTransposing || currentOffset <= -11}
        className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-slate-200 flex items-center justify-center transition-colors disabled:opacity-40 cursor-pointer"
        title="Transpose down 1 semitone"
      >
        <ArrowDown size={16} />
      </button>

      <div className="px-3 py-1 rounded-md bg-slate-950 border border-slate-800 text-center min-w-[70px]">
        <span className="text-xs font-bold text-indigo-400 block font-mono">
          {currentOffset > 0 ? `+${currentOffset}` : currentOffset}
        </span>
        <span className="text-[10px] text-slate-400 block truncate">
          {currentKey}
        </span>
      </div>

      <button
        onClick={() => onTranspose(1)}
        disabled={isTransposing || currentOffset >= 11}
        className="w-8 h-8 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-600 text-slate-200 flex items-center justify-center transition-colors disabled:opacity-40 cursor-pointer"
        title="Transpose up 1 semitone"
      >
        <ArrowUp size={16} />
      </button>

      {currentOffset !== 0 && (
        <button
          onClick={onReset}
          disabled={isTransposing}
          className="ml-1 p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
          title="Reset to original key"
        >
          <RotateCcw size={14} />
        </button>
      )}
    </div>
  );
};
