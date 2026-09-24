import React, { useState } from 'react';
import { X, Check, AlertTriangle, Sparkles } from 'lucide-react';
import type { ChordPrediction } from '../types';

interface ChordEditorModalProps {
  chord: ChordPrediction;
  chordIndex: number;
  isOpen: boolean;
  onClose: () => void;
  onSave: (index: number, newRoot: string, newQuality: string, newBass: string) => void;
}

const ROOTS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];

const QUALITIES = [
  { id: 'maj', label: 'Major (e.g. C)' },
  { id: 'min', label: 'Minor (m)' },
  { id: '7', label: 'Dominant 7th (7)' },
  { id: 'maj7', label: 'Major 7th (maj7)' },
  { id: 'min7', label: 'Minor 7th (m7)' },
  { id: 'sus4', label: 'Suspended 4th (sus4)' },
  { id: 'sus2', label: 'Suspended 2nd (sus2)' },
  { id: 'dim', label: 'Diminished (dim)' },
  { id: 'aug', label: 'Augmented (aug)' },
  { id: 'min6', label: 'Minor 6th (m6)' },
  { id: 'maj6', label: '6th (6)' },
];

export const ChordEditorModal: React.FC<ChordEditorModalProps> = ({
  chord,
  chordIndex,
  isOpen,
  onClose,
  onSave
}) => {
  const [root, setRoot] = useState(chord.root);
  const [quality, setQuality] = useState(chord.quality || 'maj');
  const [bass, setBass] = useState(chord.bass || chord.root);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(chordIndex, root, quality, bass);
    onClose();
  };

  const selectAlternative = (altChordStr: string) => {
    // Quick parse alternative
    const parts = altChordStr.split('/');
    const main = parts[0];
    const slashBass = parts[1] || null;

    // Detect root
    const rootMatch = main.match(/^([A-G][#b]?)(.*)$/);
    if (rootMatch) {
      const altRoot = rootMatch[1];
      const altQual = rootMatch[2] === 'm' ? 'min' : (rootMatch[2] || 'maj');
      setRoot(altRoot);
      setQuality(altQual);
      setBass(slashBass || altRoot);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl p-6 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div>
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>Bar {chord.bar_position || '—'} • Beat {chord.beat || chord.beat_position || 1}</span>
              {chord.needs_review && (
                <span className="flex items-center gap-1 text-[11px] font-semibold text-amber-400 bg-amber-400/10 px-2 py-0.5 rounded-full border border-amber-400/20">
                  <AlertTriangle size={12} />
                  <span>Review Needed</span>
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Detected: <span className="font-bold text-indigo-400">{chord.display}</span> • Timing: {chord.start_time.toFixed(2)}s–{chord.end_time.toFixed(2)}s (Duration: {chord.duration.toFixed(2)}s)
            </p>
          </div>

          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors cursor-pointer"
          >
            <X size={18} />
          </button>
        </div>

        {/* Alternative Model Candidates */}
        {chord.alternatives && chord.alternatives.length > 0 && (
          <div className="mb-5 p-3 rounded-xl bg-slate-950/70 border border-slate-800">
            <span className="text-xs font-semibold text-indigo-400 flex items-center gap-1 mb-2">
              <Sparkles size={13} />
              <span>Alternative Probable Candidates:</span>
            </span>
            <div className="flex flex-wrap gap-2">
              {chord.alternatives.map((alt, idx) => (
                <button
                  key={idx}
                  onClick={() => selectAlternative(alt.chord)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 flex items-center gap-1.5 transition-all cursor-pointer"
                >
                  <span>{alt.chord}</span>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {Math.round(alt.probability * 100)}%
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Form Controls */}
        <div className="space-y-4">
          {/* Root Selector */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Chord Root
            </label>
            <div className="grid grid-cols-6 gap-1.5">
              {ROOTS.map(r => (
                <button
                  key={r}
                  type="button"
                  onClick={() => {
                    setRoot(r);
                    if (bass === root) setBass(r);
                  }}
                  className={`py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
                    root === r
                      ? 'bg-indigo-600 border-indigo-500 text-white shadow-md shadow-indigo-600/30'
                      : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Quality Selector */}
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Chord Quality
            </label>
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs font-medium text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              {QUALITIES.map(q => (
                <option key={q.id} value={q.id}>{q.label}</option>
              ))}
            </select>
          </div>

          {/* Bass Note / Inversion Selector */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300">
                Bass Note (Slash Chord / Inversion)
              </label>
              <button
                type="button"
                onClick={() => setBass(root)}
                className="text-[11px] text-indigo-400 hover:underline cursor-pointer"
              >
                Reset to Root ({root})
              </button>
            </div>
            <div className="grid grid-cols-6 gap-1.5">
              {ROOTS.map(b => (
                <button
                  key={b}
                  type="button"
                  onClick={() => setBass(b)}
                  className={`py-1.5 text-xs font-bold rounded-lg border transition-all cursor-pointer ${
                    bass === b
                      ? 'bg-amber-600 border-amber-500 text-white shadow-md shadow-amber-600/30'
                      : 'bg-slate-950 border-slate-800 text-slate-300 hover:border-slate-700'
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 mt-6 border-t border-slate-800 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
          >
            <Check size={14} />
            <span>Apply Changes</span>
          </button>
        </div>
      </div>
    </div>
  );
};
