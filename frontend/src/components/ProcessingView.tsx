import React from 'react';
import { CheckCircle2, Circle, Loader2 } from 'lucide-react';
import type { AnalysisStatus } from '../types';

interface ProcessingViewProps {
  status: AnalysisStatus;
  progress: number;
  message: string;
}

interface StepItem {
  key: string;
  label: string;
  statuses: AnalysisStatus[];
}

const PIPELINE_STEPS: StepItem[] = [
  { key: 'upload', label: 'Loading audio stream', statuses: ['DOWNLOADING', 'UPLOADING', 'VALIDATING'] },
  { key: 'pre', label: 'Audio preprocessing', statuses: ['PREPROCESSING'] },
  { key: 'sep', label: 'Separating stems (Demucs GPU)', statuses: ['SEPARATING'] },
  { key: 'beat', label: 'Detecting beats & downbeats', statuses: ['ANALYZING_BEATS'] },
  { key: 'meter', label: 'Estimating time signature', statuses: ['ANALYZING_BEATS'] },
  { key: 'key', label: 'Detecting key & mode', statuses: ['ANALYZING_KEY'] },
  { key: 'chord', label: 'BTC Neural chord recognition', statuses: ['ANALYZING_CHORDS'] },
  { key: 'inv', label: 'Bass stem slash chord analysis', statuses: ['ANALYZING_INVERSION'] },
  { key: 'post', label: 'Temporal smoothing & bar alignment', statuses: ['POST_PROCESSING', 'ALIGNING_BARS'] },
  { key: 'sec', label: 'Detecting musical sections', statuses: ['DETECTING_SECTIONS'] },
  { key: 'build', label: 'Building chord sheet', statuses: ['BUILDING_SHEET'] },
];

export const ProcessingView: React.FC<ProcessingViewProps> = ({ status, progress, message }) => {
  const getStepState = (stepIndex: number) => {
    const activeStepIndex = PIPELINE_STEPS.findIndex(s => s.statuses.includes(status));
    if (status === 'COMPLETED') return 'completed';
    if (activeStepIndex === -1) return 'pending';
    if (stepIndex < activeStepIndex) return 'completed';
    if (stepIndex === activeStepIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="max-w-xl mx-auto w-full p-8 rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-purple-950/50 border border-purple-800/40 rounded-xl">
            <span className="flex h-3 w-3 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-purple-500"></span>
            </span>
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">ANALYZING SONG</h2>
            <p className="text-xs text-slate-400 mt-0.5">{message}</p>
          </div>
        </div>
        <div className="text-right">
          <span className="text-3xl font-black bg-gradient-to-r from-purple-400 to-indigo-400 bg-clip-text text-transparent">
            {progress}%
          </span>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full h-2.5 bg-slate-800 rounded-full overflow-hidden mb-6">
        <div 
          className="h-full bg-gradient-to-r from-purple-500 via-indigo-500 to-emerald-400 transition-all duration-300 rounded-full"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Featured Uiverse.io Animation Pod */}
      <div className="flex flex-col items-center justify-center py-6 mb-6 rounded-xl bg-slate-950/70 border border-purple-900/30 shadow-inner relative overflow-hidden">
        <div className="absolute inset-0 bg-radial from-purple-600/10 via-transparent to-transparent pointer-events-none" />
        <div className="loader mb-2">
          <span className="loader-text">loading</span>
          <span className="load"></span>
        </div>
        <p className="text-xs text-purple-300 font-medium tracking-wide mt-2 text-center px-4">
          {message}
        </p>
      </div>

      {/* Steps List */}
      <div className="space-y-3">
        {PIPELINE_STEPS.map((step, idx) => {
          const state = getStepState(idx);
          return (
            <div key={step.key} className="flex items-center gap-3 text-sm">
              {state === 'completed' && (
                <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
              )}
              {state === 'active' && (
                <Loader2 size={18} className="text-indigo-400 animate-spin shrink-0" />
              )}
              {state === 'pending' && (
                <Circle size={18} className="text-slate-600 shrink-0" />
              )}
              <span className={
                state === 'completed' 
                  ? 'text-slate-300 font-medium' 
                  : state === 'active' 
                  ? 'text-indigo-300 font-semibold' 
                  : 'text-slate-500'
              }>
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
