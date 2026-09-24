import React, { useState, useRef } from 'react';
import {
  Search,
  AlertCircle,
  Upload,
  Loader2,
  ExternalLink,
  Edit2,
  Sparkles,
  FileAudio,
  ArrowRight,
  FolderOpen,
  Music,
  Clock,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import type { YouTubeMetadata } from '../types';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 20, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface YouTubeSourceZoneProps {
  onStartYouTubeAnalysis: (url: string, customTitle?: string) => void;
  onStartAnalysisWithFile?: (
    file: File,
    customTitle?: string,
    youtubeMetadata?: YouTubeMetadata
  ) => void;
  onOpenExistingSong?: (songId: string) => void;
  isAnalyzing: boolean;
}

export function cleanYouTubeTitle(raw: string): string {
  if (!raw) return '';
  // Split on pipe or dash if present to remove trailing channel / branding
  let clean = raw.split(/\||–|-/)[0].trim();
  // Remove common video suffixes
  clean = clean.replace(/\((official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\)/gi, '');
  clean = clean.replace(/\[(official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\]/gi, '');
  return clean.trim() || raw.trim();
}

export const YouTubeSourceZone: React.FC<YouTubeSourceZoneProps> = ({
  onStartYouTubeAnalysis,
  onStartAnalysisWithFile,
  onOpenExistingSong,
  isAnalyzing,
}) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<(YouTubeMetadata & { existing_song_id?: string; in_library?: boolean; duration?: number }) | null>(null);
  const [customTitle, setCustomTitle] = useState('');

  // Optional local audio file override
  const [showLocalOverride, setShowLocalOverride] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleValidate = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!url.trim()) return;

    setError(null);
    setMetadata(null);
    setLoading(true);

    try {
      const res = await fetch('/api/sources/youtube/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Could not validate YouTube URL.');
      }

      setMetadata(data);
      const cleaned = cleanYouTubeTitle(data.title || '');
      setCustomTitle(cleaned);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect YouTube link.');
    } finally {
      setLoading(false);
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text);
        if (text.includes('youtube.com') || text.includes('youtu.be')) {
          // Auto-trigger validate on clean paste
          setTimeout(() => {
            const submitBtn = document.getElementById('btn-youtube-inspect');
            if (submitBtn) submitBtn.click();
          }, 50);
        }
      }
    } catch (err) {
      console.warn('Clipboard read failed:', err);
    }
  };

  const handleResetToClean = () => {
    if (metadata?.title) {
      setCustomTitle(cleanYouTubeTitle(metadata.title));
    }
  };

  const handleResetToRaw = () => {
    if (metadata?.title) {
      setCustomTitle(metadata.title);
    }
  };

  // Drag and drop handlers for local audio file
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const isValidAudio = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma'].includes(ext || '');
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isValidAudio(file.name)) {
        setSelectedFile(file);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
    }
  };

  const formatFileSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  const formatDuration = (secs?: number) => {
    if (!secs) return null;
    const mins = Math.floor(secs / 60);
    const rem = Math.floor(secs % 60);
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  const handleDirectYouTubeAnalyze = () => {
    if (!url.trim()) return;
    onStartYouTubeAnalysis(url.trim(), customTitle.trim() || metadata?.title);
  };

  const handleFileAnalyze = () => {
    if (!selectedFile || !onStartAnalysisWithFile) return;
    onStartAnalysisWithFile(selectedFile, customTitle.trim() || metadata?.title, metadata || undefined);
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6">
      {/* Top Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400 shrink-0">
          <YoutubeIcon size={22} />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">Analyze Directly from YouTube</h3>
          <p className="text-xs text-slate-400">
            Paste any YouTube video or song link to automatically extract audio and recognize chords.
          </p>
        </div>
      </div>

      {/* URL Input Form */}
      <form onSubmit={handleValidate} className="space-y-3">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <input
              type="text"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                if (error) setError(null);
              }}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-4 pr-16 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 font-mono transition-colors"
            />
            {url && (
              <button
                type="button"
                onClick={() => {
                  setUrl('');
                  setMetadata(null);
                  setError(null);
                  setSelectedFile(null);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 px-2 py-1 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 text-[11px] font-semibold cursor-pointer transition-colors shadow-sm"
              >
                Clear
              </button>
            )}
          </div>

          <button
            type="button"
            onClick={handlePaste}
            className="px-3.5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 cursor-pointer transition-colors shrink-0"
            title="Paste from clipboard"
          >
            Paste
          </button>

          <button
            id="btn-youtube-inspect"
            type="submit"
            disabled={loading || !url.trim()}
            className="px-5 py-3 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-red-600/30 transition-all cursor-pointer whitespace-nowrap shrink-0"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            <span>Fetch Video</span>
          </button>
        </div>
      </form>

      {/* Validation Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/80 text-red-300 flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 text-red-400 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold">Unable to fetch video</p>
            <p className="mt-0.5 text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Step 2: Validated Video Metadata Card */}
      {metadata && metadata.valid && (
        <div className="border border-slate-800 rounded-2xl bg-slate-950/70 overflow-hidden divide-y divide-slate-800 animate-in fade-in duration-200">
          <div className="p-4 sm:p-5 flex flex-col sm:flex-row gap-4">
            {metadata.thumbnail_url && (
              <img
                src={metadata.thumbnail_url}
                alt={metadata.title || "YouTube thumbnail"}
                className="w-full sm:w-44 h-28 object-cover rounded-xl border border-slate-800 bg-slate-900 shrink-0 shadow-md"
              />
            )}

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-[10px] font-bold text-red-400 tracking-wider uppercase">
                  YouTube Video
                </span>
                {metadata.duration && (
                  <span className="text-[10px] text-slate-400 font-medium flex items-center gap-1 bg-slate-900 px-2 py-0.5 rounded-full border border-slate-800">
                    <Clock size={10} />
                    <span>{formatDuration(metadata.duration)}</span>
                  </span>
                )}
              </div>

              <h4 className="text-sm sm:text-base font-bold text-white line-clamp-2" title={metadata.title}>
                {metadata.title}
              </h4>
              <p className="text-xs text-slate-400 mt-1 font-medium">
                Channel: <span className="text-slate-200">{metadata.channel || 'Unknown Creator'}</span>
              </p>

              <div className="flex items-center gap-3 mt-3">
                {metadata.canonical_url && (
                  <a
                    href={metadata.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 text-xs font-semibold transition-colors"
                  >
                    <span>Watch on YouTube</span>
                    <ExternalLink size={12} />
                  </a>
                )}

                {metadata.in_library && metadata.existing_song_id && onOpenExistingSong && (
                  <button
                    type="button"
                    onClick={() => onOpenExistingSong(metadata.existing_song_id!)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold cursor-pointer transition-colors"
                  >
                    <FolderOpen size={12} />
                    <span>In Library (Open Chart)</span>
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Editable Song Title */}
          <div className="p-4 sm:p-5 bg-slate-900/60">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Edit2 size={13} className="text-indigo-400" />
                <span>Song Title for Chord Sheet & Library:</span>
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetToClean}
                  className="text-[10px] font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
                  title="Auto-clean title by stripping artist tags and video suffixes"
                >
                  <Sparkles size={11} />
                  <span>Auto-Clean</span>
                </button>
                <button
                  type="button"
                  onClick={handleResetToRaw}
                  className="text-[10px] font-medium text-slate-400 hover:text-slate-300 cursor-pointer"
                  title="Reset to full YouTube video title"
                >
                  Original
                </button>
              </div>
            </div>

            <input
              type="text"
              value={customTitle}
              onChange={(e) => setCustomTitle(e.target.value)}
              placeholder="e.g. Song Title"
              className="w-full bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded-xl px-3.5 py-2.5 text-sm font-bold text-white focus:outline-none transition-colors"
            />
            <p className="text-[11px] text-slate-400 mt-1.5">
              The title will appear on your interactive chord chart, PDF export, and saved song library.
            </p>
          </div>

          {/* Primary Action Button: Direct Video Analysis */}
          <div className="p-4 sm:p-5 bg-slate-950/80 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <p className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Sparkles size={14} className="text-red-400" />
                <span>Ready to recognize chords from this video</span>
              </p>
              <p className="text-[11px] text-slate-400 mt-0.5">
                Extracts the audio stream automatically and processes with Demucs GPU stem separation & BTC Transformer models.
              </p>
            </div>

            <button
              type="button"
              onClick={handleDirectYouTubeAnalyze}
              disabled={isAnalyzing}
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-gradient-to-r from-red-600 via-rose-600 to-indigo-600 hover:from-red-500 hover:via-rose-500 hover:to-indigo-500 disabled:opacity-50 text-white text-xs sm:text-sm font-black flex items-center justify-center gap-2 shadow-xl shadow-red-600/25 cursor-pointer transition-all whitespace-nowrap"
            >
              <Music size={16} />
              <span>Generate Chords from Video</span>
              <ArrowRight size={16} />
            </button>
          </div>

          {/* Optional Local File Override Accordion */}
          {onStartAnalysisWithFile && (
            <div className="p-4 bg-slate-900/40 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setShowLocalOverride(!showLocalOverride)}
                className="w-full flex items-center justify-between text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors py-1 cursor-pointer"
              >
                <span>Prefer to attach your own local audio file instead?</span>
                {showLocalOverride ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>

              {showLocalOverride && (
                <div className="mt-3 pt-3 border-t border-slate-800/60 space-y-3">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".mp3,.wav,.flac,.m4a,.aac,.ogg,.wma"
                    className="hidden"
                    onChange={handleFileChange}
                  />

                  {!selectedFile ? (
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      onDragEnter={handleDrag}
                      onDragLeave={handleDrag}
                      onDragOver={handleDrag}
                      onDrop={handleDrop}
                      className={`border-2 border-dashed rounded-xl p-5 text-center cursor-pointer transition-all ${
                        dragActive
                          ? 'border-indigo-500 bg-indigo-950/30'
                          : 'border-slate-700 hover:border-slate-500 bg-slate-950/60'
                      }`}
                    >
                      <Upload size={18} className="mx-auto text-slate-400 mb-1" />
                      <p className="text-xs font-bold text-slate-200">
                        Select Local Audio (MP3, WAV, FLAC, M4A)
                      </p>
                      <p className="text-[10px] text-slate-500">
                        Click to browse or drag & drop
                      </p>
                    </div>
                  ) : (
                    <div className="p-3 rounded-xl bg-slate-950 border border-emerald-500/30 flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <FileAudio size={18} className="text-emerald-400 shrink-0" />
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-white truncate max-w-xs" title={selectedFile.name}>
                            {selectedFile.name}
                          </p>
                          <p className="text-[10px] text-slate-400">
                            {formatFileSize(selectedFile.size)}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => fileInputRef.current?.click()}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-semibold transition-colors"
                        >
                          Change
                        </button>
                        <button
                          type="button"
                          onClick={handleFileAnalyze}
                          disabled={isAnalyzing}
                          className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all"
                        >
                          Analyze Local Audio
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default YouTubeSourceZone;
