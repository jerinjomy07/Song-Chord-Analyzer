import React, { useState, useEffect, useRef } from 'react';
import { UploadZone } from './components/UploadZone';
import { ProcessingView } from './components/ProcessingView';
import { SongHeader } from './components/SongHeader';
import { AudioPlayerTimeline } from './components/AudioPlayerTimeline';
import { ChordSheet } from './components/ChordSheet';
import { ChordEditorModal } from './components/ChordEditorModal';
import { TransposerToolbar } from './components/TransposerToolbar';
import { ExportToolbar } from './components/ExportToolbar';
import { YouTubeSourceZone } from './components/YouTubeSourceZone';
import type { SongAnalysis, AnalysisStatus, ChordPrediction } from './types';
import { Music2, AlertCircle, Upload } from 'lucide-react';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 16, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

export const App: React.FC = () => {
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<SongAnalysis | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>('IDLE');
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Input Source State ('upload' | 'youtube')
  const [inputSource, setInputSource] = useState<'upload' | 'youtube'>('upload');

  // Audio Player State
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState<number>(1);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handleVolumeChange = (newVol: number) => {
    setVolume(newVol);
    if (audioRef.current) {
      audioRef.current.volume = newVol;
    }
  };

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

        {/* View 1: Input Source Selector & Upload / YouTube */}
        {status === 'IDLE' && !analysis && (
          <div className="py-8 sm:py-12">
            <div className="text-center max-w-xl mx-auto mb-8">
              <h2 className="text-3xl sm:text-4xl font-black text-white tracking-tight mb-3">
                Automatic Music Transcription for Musicians
              </h2>
              <p className="text-slate-400 text-sm sm:text-base">
                Automatic Demucs stem separation, BTC neural chord recognition, and bass inversion tracking produce a clean, musician-friendly chord chart.
              </p>
            </div>

            {/* Input Source Toggle */}
            <div className="flex flex-col items-center gap-2 mb-8">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">INPUT SOURCE</span>
              <div className="bg-slate-950 p-1.5 rounded-2xl border border-slate-800 flex items-center gap-1 shadow-lg">
                <button
                  onClick={() => setInputSource('upload')}
                  className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                    inputSource === 'upload'
                      ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  <Upload size={14} />
                  <span>Upload Audio</span>
                </button>

                <button
                  onClick={() => setInputSource('youtube')}
                  className={`px-5 py-2.5 rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center gap-2 ${
                    inputSource === 'youtube'
                      ? 'bg-red-600 text-white shadow-md shadow-red-600/30'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                  }`}
                >
                  <YoutubeIcon size={14} />
                  <span>YouTube Link</span>
                </button>
              </div>
            </div>

            {/* Active Source Zone */}
            {inputSource === 'upload' ? (
              <UploadZone
                onStartAnalysis={handleStartAnalysis}
                isAnalyzing={false}
              />
            ) : (
              <YouTubeSourceZone
                onSwitchToUpload={() => setInputSource('upload')}
              />
            )}
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

            {/* Interactive Timeline & Audio Waveform Player with Live Indicators & Volume */}
            <AudioPlayerTimeline
              analysis={analysis}
              currentTime={currentTime}
              isPlaying={isPlaying}
              onPlayPause={handlePlayPause}
              onSeek={handleSeek}
              onSelectChord={(chord, idx) => setSelectedChord({ chord, index: idx })}
              volume={volume}
              onVolumeChange={handleVolumeChange}
            />

            {/* Musician-Friendly Chord Sheet with Synchronized Auto-Scroll & Seeking */}
            <ChordSheet
              analysis={analysis}
              currentTime={currentTime}
              isPlaying={isPlaying}
              onSeek={handleSeek}
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
