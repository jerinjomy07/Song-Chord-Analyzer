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
  CheckCircle2,
  FolderOpen
} from 'lucide-react';
import type { YouTubeMetadata } from '../types';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 20, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface YouTubeSourceZoneProps {
  onStartAnalysis: (
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
  onStartAnalysis,
  onOpenExistingSong,
  isAnalyzing,
}) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<YouTubeMetadata & { existing_song_id?: string; in_library?: boolean } | null>(null);
  const [customTitle, setCustomTitle] = useState('');

  // Audio file selection
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

  const handleSubmitAnalysis = () => {
    if (!selectedFile) return;
    onStartAnalysis(selectedFile, customTitle.trim() || metadata?.title, metadata || undefined);
  };

  return (
    <div className="w-full max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl space-y-6">
      {/* Top Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400 shrink-0">
          <YoutubeIcon size={22} />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">YouTube Link Input</h3>
          <p className="text-xs text-slate-400">
            Paste a public YouTube link to inspect video reference details and pair with your audio.
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
            type="submit"
            disabled={loading || !url.trim()}
            className="px-5 py-3 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-red-600/30 transition-all cursor-pointer whitespace-nowrap shrink-0"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            <span>Continue</span>
          </button>
        </div>
      </form>

      {/* Validation Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/40 border border-red-800/80 text-red-300 flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 text-red-400 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold">Invalid YouTube Link</p>
            <p className="mt-0.5 text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Step 2: Validated Video Metadata Card */}
      {metadata && metadata.valid && (
        <div className="border border-slate-800 rounded-2xl bg-slate-950/60 overflow-hidden divide-y divide-slate-800">
          <div className="p-4 sm:p-5 flex flex-col sm:flex-row gap-4">
            {metadata.thumbnail_url && (
              <img
                src={metadata.thumbnail_url}
                alt={metadata.title || "YouTube thumbnail"}
                className="w-full sm:w-44 h-28 object-cover rounded-xl border border-slate-800 bg-slate-900 shrink-0"
              />
            )}

            <div className="flex-1 min-w-0">
              <span className="text-[10px] font-bold text-red-400 tracking-wider uppercase block mb-1">
                Identified YouTube Video
              </span>
              <h4 className="text-sm sm:text-base font-bold text-white line-clamp-2" title={metadata.title}>
                {metadata.title}
              </h4>
              <p className="text-xs text-slate-400 mt-1 font-medium">
                Channel: <span className="text-slate-200">{metadata.channel || 'Unknown Creator'}</span>
              </p>
              {metadata.canonical_url && (
                <div className="flex items-center gap-3 mt-3">
                  <a
                    href={metadata.canonical_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 text-xs font-semibold transition-colors"
                  >
                    <span>Open on YouTube</span>
                    <ExternalLink size={12} />
                  </a>

                  {metadata.in_library && metadata.existing_song_id && onOpenExistingSong && (
                    <button
                      type="button"
                      onClick={() => onOpenExistingSong(metadata.existing_song_id!)}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-semibold cursor-pointer transition-colors"
                    >
                      <FolderOpen size={12} />
                      <span>Already in Library (Open)</span>
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Editable Song Title */}
          <div className="p-4 sm:p-5 bg-slate-900/60">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Edit2 size={13} className="text-indigo-400" />
                <span>Song Title for Analysis & Sheet:</span>
              </label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetToClean}
                  className="text-[10px] font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1 cursor-pointer"
                  title="Auto-clean title by stripping artist tags and suffixes"
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
              Customize how the song name will appear on your chord chart, library, and exports.
            </p>
          </div>

          {/* Audio Selection Area (Policy Compliant) */}
          <div className="p-4 sm:p-5 bg-amber-950/20 space-y-4">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-amber-200 uppercase tracking-wide">
                  This app needs audio that you are authorized to analyze
                </p>
                <p className="text-xs text-amber-300/90 mt-1 leading-relaxed">
                  Direct stream ripping/downloading from YouTube is restricted by copyright and terms of service.
                  Please choose your local audio file (<span className="font-mono text-amber-200">MP3, WAV, FLAC, M4A</span>)
                  for this song to begin chord recognition.
                </p>
              </div>
            </div>

            {/* Local Audio File Selector */}
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
                className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                  dragActive
                    ? 'border-amber-400 bg-amber-950/40'
                    : 'border-amber-500/40 hover:border-amber-400 bg-slate-950/60'
                }`}
              >
                <div className="w-10 h-10 rounded-full bg-amber-500/20 text-amber-300 flex items-center justify-center mx-auto mb-2">
                  <Upload size={20} />
                </div>
                <p className="text-sm font-bold text-slate-200 mb-1">
                  Choose Local Audio File
                </p>
                <p className="text-xs text-slate-400">
                  Click to browse or drag & drop MP3, WAV, FLAC, or M4A
                </p>
              </div>
            ) : (
              <div className="p-3.5 rounded-xl bg-slate-950/80 border border-emerald-500/30 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                    <FileAudio size={20} />
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-white truncate max-w-xs sm:max-w-md" title={selectedFile.name}>
                        {selectedFile.name}
                      </span>
                      <CheckCircle2 size={13} className="text-emerald-400 shrink-0" />
                    </div>
                    <p className="text-[11px] text-slate-400">
                      {formatFileSize(selectedFile.size)} • {selectedFile.name.split('.').pop()?.toUpperCase()}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold cursor-pointer shrink-0 transition-colors"
                >
                  Change File
                </button>
              </div>
            )}

            {/* Final Action Button */}
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={handleSubmitAnalysis}
                disabled={!selectedFile || isAnalyzing}
                className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-indigo-600 hover:from-red-500 hover:to-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs sm:text-sm font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/20 cursor-pointer transition-all"
              >
                <span>Analyze Song</span>
                <ArrowRight size={16} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default YouTubeSourceZone;
