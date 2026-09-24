import React, { useState, useEffect, useRef } from 'react';
import { UploadZone } from './components/UploadZone';
import { ProcessingView } from './components/ProcessingView';
import { SongHeader } from './components/SongHeader';
import { AudioPlayerTimeline } from './components/AudioPlayerTimeline';
import { ChordSheet } from './components/ChordSheet';
import { ChordEditorModal } from './components/ChordEditorModal';
import { TransposerToolbar } from './components/TransposerToolbar';
import { ExportToolbar } from './components/ExportToolbar';
import type { SongAnalysis, AnalysisStatus, ChordPrediction } from './types';
import { Music2, AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<SongAnalysis | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>('IDLE');
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Audio Player State
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Chord Editor Modal State
  const [selectedChord, setSelectedChord] = useState<{ chord: ChordPrediction; index: number } | null>(null);
  const [isTransposing, setIsTransposing] = useState(false);

  // Polling for analysis progress
  useEffect(() => {
    if (!analysisId || status === 'COMPLETED' || status === 'FAILED' || status === 'IDLE') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/analysis/${analysisId}/status`);
        if (!res.ok) throw new Error('Status check failed');
        const data = await res.json();

        setStatus(data.status);
        setProgress(data.progress);
        setStatusMessage(data.message);

        if (data.status === 'COMPLETED') {
          clearInterval(interval);
          // Fetch full analysis result
          const analysisRes = await fetch(`/api/analysis/${analysisId}`);
          if (analysisRes.ok) {
            const fullData: SongAnalysis = await analysisRes.json();
            setAnalysis(fullData);
          }
        } else if (data.status === 'FAILED') {
          clearInterval(interval);
          setErrorMessage(data.error || 'Audio analysis failed.');
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [analysisId, status]);

  // Audio element time tracking
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => setCurrentTime(audio.currentTime);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [analysis]);

  const handleStartAnalysis = async (file: File) => {
    setErrorMessage(null);
    setAnalysis(null);
    setStatus('UPLOADING');
    setProgress(5);
    setStatusMessage('Uploading music file...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));

    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Upload failed');
      }

      const data = await res.json();
      setAnalysisId(data.analysis_id);
      setStatus('PREPROCESSING');
      setProgress(10);
      setStatusMessage('Queued for processing...');
    } catch (err: any) {
      setStatus('FAILED');
      setErrorMessage(err.message || 'Could not connect to analysis service.');
    }
  };

  const handlePlayPause = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play().catch(e => console.error("Playback error:", e));
      setIsPlaying(true);
    }
  };

  const handleSeek = (timeSec: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = timeSec;
      setCurrentTime(timeSec);
    }
  };

  const handleTranspose = async (semitones: number) => {
    if (!analysisId || !analysis) return;
    setIsTransposing(true);
    try {
      const res = await fetch(`/api/analysis/${analysisId}/transpose`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ semitones }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAnalysis(updated);
      }
    } catch (err) {
      console.error('Transposition error:', err);
    } finally {
      setIsTransposing(false);
    }
  };

  const handleSaveChordEdit = async (
    index: number,
    newRoot: string,
    newQuality: string,
    newBass: string
  ) => {
    if (!analysisId) return;
    try {
      const res = await fetch(`/api/analysis/${analysisId}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chord_index: index,
          new_root: newRoot,
          new_quality: newQuality,
          new_bass: newBass,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAnalysis(updated);
      }
    } catch (err) {
      console.error('Error saving chord edit:', err);
    }
  };

  const handleRenameSection = async (sectionId: string, newName: string) => {
    if (!analysisId) return;
    try {
      const res = await fetch(`/api/analysis/${analysisId}/rename-section`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_id: sectionId,
          new_name: newName,
        }),
      });
      if (res.ok) {
        const updated = await res.json();
        setAnalysis(updated);
      }
    } catch (err) {
      console.error('Error renaming section:', err);
    }
  };

  const handleReset = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setAnalysis(null);
    setAnalysisId(null);
    setStatus('IDLE');
    setProgress(0);
    setCurrentTime(0);
    setIsPlaying(false);
    setErrorMessage(null);
  };

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/50 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Music2 size={22} />
            </div>
            <div>
              <span className="font-extrabold text-lg tracking-tight text-white block">
                SONG CHORD ANALYZER
              </span>
              <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase block">
                Automatic MIR & Chord Recognition
              </span>
            </div>
          </div>

          {analysis && (
            <div className="flex items-center gap-3">
              <TransposerToolbar
                currentOffset={analysis.transpose_semitones}
                currentKey={analysis.key.display}
                onTranspose={handleTranspose}
                onReset={() => handleTranspose(-analysis.transpose_semitones)}
                isTransposing={isTransposing}
              />
              <ExportToolbar analysisId={analysis.id} />
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 py-8">
        {/* Error Banner */}
        {errorMessage && (
          <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-300 flex items-start gap-3">
            <AlertCircle size={20} className="shrink-0 text-red-400 mt-0.5" />
            <div>
              <p className="font-semibold text-sm">Analysis Notice</p>
              <p className="text-xs text-red-300 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* View 1: Upload Music */}
        {status === 'IDLE' && !analysis && (
          <div className="py-12">
            <div className="text-center max-w-xl mx-auto mb-10">
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight mb-3">
                Automatic Music Transcription for Musicians
              </h2>
              <p className="text-slate-400 text-sm sm:text-base">
                Upload your song file. Automatic Demucs stem separation, BTC neural chord recognition, and bass inversion tracking produce a clean, editable chord chart.
              </p>
            </div>

            <UploadZone
              onStartAnalysis={handleStartAnalysis}
              isAnalyzing={false}
            />
          </div>
        )}

        {/* View 2: Processing in Progress */}
        {status !== 'IDLE' && status !== 'COMPLETED' && status !== 'FAILED' && (
          <div className="py-16">
            <ProcessingView
              status={status}
              progress={progress}
              message={statusMessage}
            />
          </div>
        )}

        {/* View 3: Completed Analysis Results */}
        {analysis && (
          <div>
            {/* Audio Element */}
            {analysis.audio_url && (
              <audio
                ref={audioRef}
                src={analysis.audio_url}
                preload="metadata"
              />
            )}

            {/* Song Information Badges */}
            <SongHeader
              analysis={analysis}
              onReset={handleReset}
            />

            {/* Interactive Timeline & Audio Waveform Player */}
            <AudioPlayerTimeline
              analysis={analysis}
              currentTime={currentTime}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onSeek={handleSeek}
              onSelectChord={(chord, idx) => setSelectedChord({ chord, index: idx })}
            />

            {/* Musician-Friendly Chord Sheet */}
            <ChordSheet
              analysis={analysis}
              currentTime={currentTime}
              onSelectChord={(chord, idx) => setSelectedChord({ chord, index: idx })}
              onRenameSection={handleRenameSection}
            />
          </div>
        )}
      </main>

      {/* Chord Editor Modal */}
      {selectedChord && (
        <ChordEditorModal
          chord={selectedChord.chord}
          chordIndex={selectedChord.index}
          isOpen={true}
          onClose={() => setSelectedChord(null)}
          onSave={handleSaveChordEdit}
        />
      )}

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-500">
        <p>Song Chord Analyzer • Dedicated Automatic Chord Recognition & Inversion Transcription</p>
      </footer>
    </div>
  );
};

export default App;
