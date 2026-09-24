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
import { HistoryPage } from './components/HistoryPage';
import { RecentSongsSection } from './components/RecentSongsSection';
import { DuplicateModal } from './components/DuplicateModal';
import type { SongAnalysis, AnalysisStatus, ChordPrediction, HistorySong, YouTubeMetadata } from './types';
import { Music2, Music, AlertCircle, Upload, Home, Library, Check } from 'lucide-react';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 16, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

type NavTab = 'home' | 'history' | 'analysis';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<NavTab>('home');
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<SongAnalysis | null>(null);
  const [status, setStatus] = useState<AnalysisStatus>('IDLE');
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Library & Duplicate State
  const [duplicateInfo, setDuplicateInfo] = useState<{
    existingSong: HistorySong;
    file?: File;
    youtubeUrl?: string;
    customTitle?: string;
    youtubeMeta?: YouTubeMetadata;
  } | null>(null);
  const [recentRefreshTrigger, setRecentRefreshTrigger] = useState(0);
  const [prefilledTitle, setPrefilledTitle] = useState<string>('');

  // Auto-Save Indicator State
  const [savedIndicator, setSavedIndicator] = useState(false);
  const savedTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const triggerSavedIndicator = () => {
    setSavedIndicator(true);
    if (savedTimerRef.current) clearTimeout(savedTimerRef.current);
    savedTimerRef.current = setTimeout(() => {
      setSavedIndicator(false);
    }, 2500);
    setRecentRefreshTrigger(prev => prev + 1);
  };

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
            setCurrentTab('analysis');
            setRecentRefreshTrigger(prev => prev + 1);
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

  const handleStartAnalysis = async (
    file: File,
    force: boolean = false,
    customTitle?: string,
    youtubeMeta?: YouTubeMetadata
  ) => {
    setErrorMessage(null);
    setDuplicateInfo(null);
    setAnalysis(null);
    setStatus('UPLOADING');
    setProgress(5);
    setStatusMessage('Uploading music file...');

    const finalTitle = customTitle?.trim() || prefilledTitle?.trim() || file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' ');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('title', finalTitle);
    if (force) {
      formData.append('force', 'true');
    }
    if (youtubeMeta && youtubeMeta.video_id) {
      formData.append('source_type', 'youtube_reference');
      formData.append('youtube_video_id', youtubeMeta.video_id);
      if (youtubeMeta.canonical_url) formData.append('youtube_url', youtubeMeta.canonical_url);
      if (youtubeMeta.title) formData.append('youtube_title', youtubeMeta.title);
      if (youtubeMeta.channel) formData.append('youtube_channel', youtubeMeta.channel);
    } else {
      formData.append('source_type', 'local');
    }

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

      if (data.status === 'DUPLICATE_FOUND') {
        setStatus('IDLE');
        setDuplicateInfo({ existingSong: data.existing_song, file, customTitle, youtubeMeta });
        return;
      }

      setAnalysisId(data.analysis_id);
      setStatus('PREPROCESSING');
      setProgress(10);
      setStatusMessage('Queued for processing...');
    } catch (err: any) {
      setStatus('FAILED');
      setErrorMessage(err.message || 'Could not connect to analysis service.');
    }
  };

  const handleStartYouTubeAnalysis = async (url: string, customTitle?: string, force: boolean = false) => {
    setErrorMessage(null);
    setDuplicateInfo(null);
    setAnalysis(null);
    setStatus('DOWNLOADING');
    setProgress(5);
    setStatusMessage('Connecting to YouTube and extracting audio stream...');

    try {
      const res = await fetch('/api/analyze/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url,
          title: customTitle?.trim() || undefined,
          force
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to start YouTube analysis');
      }

      const data = await res.json();

      if (data.status === 'DUPLICATE_FOUND') {
        setStatus('IDLE');
        setDuplicateInfo({ existingSong: data.existing_song, youtubeUrl: url, customTitle });
        return;
      }

      setAnalysisId(data.analysis_id);
      setProgress(10);
      setStatusMessage('Extracting audio from YouTube video...');
    } catch (err: any) {
      setStatus('FAILED');
      setErrorMessage(err.message || 'Could not connect to YouTube analysis service.');
    }
  };

  const openSongFromHistory = async (songId: string) => {
    setErrorMessage(null);
    setDuplicateInfo(null);
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsPlaying(false);
    setCurrentTime(0);

    try {
      const res = await fetch(`/api/history/${songId}/open`);
      if (!res.ok) {
        throw new Error('Failed to load song from history.');
      }
      const fullData: SongAnalysis = await res.json();
      setAnalysisId(songId);
      setAnalysis(fullData);
      setStatus('COMPLETED');
      setCurrentTab('analysis');
      setRecentRefreshTrigger(prev => prev + 1);
    } catch (err: any) {
      console.error('Failed to open song:', err);
      setErrorMessage(err.message || 'Could not open historical song.');
    }
  };

  const handleStartReanalyze = (songId: string) => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setIsPlaying(false);
    setCurrentTime(0);
    setAnalysis(null);
    setAnalysisId(songId);
    setStatus('PREPROCESSING');
    setProgress(5);
    setStatusMessage('Re-analyzing audio with Demucs & BTC...');
    setCurrentTab('home');
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
        triggerSavedIndicator();
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
        triggerSavedIndicator();
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
        triggerSavedIndicator();
      }
    } catch (err) {
      console.error('Error renaming section:', err);
    }
  };

  const handleRenameCurrentSong = async (newTitle: string) => {
    if (!analysisId || !analysis || !newTitle.trim()) return;
    try {
      const res = await fetch(`/api/history/${analysisId}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle.trim() }),
      });
      if (res.ok) {
        setAnalysis(prev => (prev ? { ...prev, title: newTitle.trim() } : null));
        triggerSavedIndicator();
      }
    } catch (err) {
      console.error('Failed to rename current song:', err);
    }
  };

  const handleReset = () => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    setAnalysis(null);
    setAnalysisId(null);
    setPrefilledTitle('');
    setStatus('IDLE');
    setProgress(0);
    setCurrentTime(0);
    setIsPlaying(false);
    setErrorMessage(null);
    setCurrentTab('home');
    setRecentRefreshTrigger(prev => prev + 1);
  };

  const isProcessing = status !== 'IDLE' && status !== 'COMPLETED' && status !== 'FAILED';

  return (
    <div className="min-h-screen bg-[#0b0f19] text-slate-100 flex flex-col">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          {/* Logo & Branding */}
          <div
            onClick={() => setCurrentTab('home')}
            className="flex items-center gap-3 cursor-pointer select-none shrink-0"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Music2 size={22} />
            </div>
            <div>
              <span className="font-extrabold text-base sm:text-lg tracking-tight text-white block">
                SONG CHORD ANALYZER
              </span>
              <span className="text-[10px] font-semibold text-slate-400 tracking-wider uppercase block">
                Automatic MIR & Chord Recognition
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800 shrink-0">
            <button
              onClick={() => setCurrentTab('home')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                currentTab === 'home'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Home size={13} />
              <span>Home</span>
            </button>

            <button
              onClick={() => setCurrentTab('history')}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                currentTab === 'history'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Library size={13} />
              <span>History</span>
            </button>

            {analysis && (
              <button
                onClick={() => setCurrentTab('analysis')}
                className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                  currentTab === 'analysis'
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`}
                title={analysis.title}
              >
                <Music size={13} />
                <span className="max-w-[110px] sm:max-w-[150px] truncate">{analysis.title}</span>
              </button>
            )}
          </nav>

          {/* Right Toolbar / Saved Indicator */}
          {analysis && (
            <div className="flex items-center gap-2 sm:gap-3 shrink-0">
              {/* Auto-Save Feedback Badge */}
              {savedIndicator && (
                <div className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold animate-in fade-in duration-200">
                  <Check size={12} className="text-emerald-400" />
                  <span>Saved</span>
                </div>
              )}

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
              <p className="font-semibold text-sm">Notice</p>
              <p className="text-xs text-red-300 mt-0.5">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* View 1: Processing in Progress */}
        {isProcessing && (
          <div className="py-16">
            <ProcessingView
              status={status}
              progress={progress}
              message={statusMessage}
            />
          </div>
        )}

        {/* View 2: History Library Page */}
        {!isProcessing && currentTab === 'history' && (
          <HistoryPage
            onOpenSong={openSongFromHistory}
            onNavigateHome={() => setCurrentTab('home')}
            onStartReanalyze={handleStartReanalyze}
          />
        )}

        {/* View 3: Home / Upload & Source Selection */}
        {!isProcessing && currentTab === 'home' && (
          <div className="py-6 sm:py-10">
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
                onStartAnalysis={(file, customTitle) => handleStartAnalysis(file, false, customTitle)}
                isAnalyzing={false}
                prefilledTitle={prefilledTitle}
              />
            ) : (
              <YouTubeSourceZone
                onStartYouTubeAnalysis={handleStartYouTubeAnalysis}
                onStartAnalysisWithFile={(file, customTitle, ytMeta) => handleStartAnalysis(file, false, customTitle, ytMeta)}
                onOpenExistingSong={openSongFromHistory}
                isAnalyzing={isProcessing}
              />
            )}

            {/* Quick Access Recent Songs */}
            <RecentSongsSection
              onOpenSong={openSongFromHistory}
              onNavigateHistory={() => setCurrentTab('history')}
              refreshTrigger={recentRefreshTrigger}
            />
          </div>
        )}

        {/* View 4: Completed Analysis Results */}
        {!isProcessing && currentTab === 'analysis' && analysis && (
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
              onRenameTitle={handleRenameCurrentSong}
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

      {/* Duplicate Detection Modal */}
      {duplicateInfo && (
        <DuplicateModal
          existingSong={duplicateInfo.existingSong}
          fileName={duplicateInfo.file ? duplicateInfo.file.name : (duplicateInfo.existingSong.title || 'YouTube Video')}
          onOpenExisting={(id) => {
            setDuplicateInfo(null);
            openSongFromHistory(id);
          }}
          onAnalyzeAgain={() => {
            const file = duplicateInfo.file;
            const ytUrl = duplicateInfo.youtubeUrl;
            const customTitle = duplicateInfo.customTitle;
            const ytMeta = duplicateInfo.youtubeMeta;
            setDuplicateInfo(null);
            if (ytUrl) {
              handleStartYouTubeAnalysis(ytUrl, customTitle, true);
            } else if (file) {
              handleStartAnalysis(file, true, customTitle, ytMeta);
            }
          }}
          onCancel={() => {
            setDuplicateInfo(null);
            setStatus('IDLE');
          }}
        />
      )}

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
