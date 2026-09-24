import React, { useState } from 'react';
import { Search, AlertCircle, Upload, Loader2, ExternalLink, Edit2, Sparkles } from 'lucide-react';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 20, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface YouTubeSourceZoneProps {
  onSwitchToUpload: (suggestedTitle?: string) => void;
}

interface YouTubeMetadata {
  valid: boolean;
  video_id?: string;
  title?: string;
  channel?: string;
  thumbnail_url?: string;
  canonical_url?: string;
  compliance_message?: string;
  authorized_audio_available?: boolean;
}

export function cleanYouTubeTitle(raw: string): string {
  if (!raw) return '';
  // Split on pipe or dash if present
  let clean = raw.split(/\||–|-/)[0].trim();
  // Remove common suffixes like (Official Video), [Official Audio], etc.
  clean = clean.replace(/\((official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\)/gi, '');
  clean = clean.replace(/\[(official\s*(music\s*)?(video|audio|lyric|video\s*song)|lyrics?|4k|hd|remastered)\]/gi, '');
  return clean.trim() || raw.trim();
}

export const YouTubeSourceZone: React.FC<YouTubeSourceZoneProps> = ({ onSwitchToUpload }) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<YouTubeMetadata | null>(null);
  const [customTitle, setCustomTitle] = useState('');

  const handleValidate = async (e: React.FormEvent) => {
    e.preventDefault();
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

  return (
    <div className="w-full max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
          <YoutubeIcon size={22} />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">YouTube Link Inspection</h3>
          <p className="text-xs text-slate-400">
            Paste a public YouTube link to inspect video details and prepare for chord analysis.
          </p>
        </div>
      </div>

      {/* URL Input Form with generous right padding to prevent Clear button collision */}
      <form onSubmit={handleValidate} className="space-y-4">
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
            className="px-3.5 py-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 cursor-pointer transition-colors"
            title="Paste from clipboard"
          >
            Paste
          </button>

          <button
            type="submit"
            disabled={loading || !url.trim()}
            className="px-5 py-3 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-red-600/30 transition-all cursor-pointer whitespace-nowrap"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            <span>Inspect Link</span>
          </button>
        </div>
      </form>

      {/* Validation Error Message */}
      {error && (
        <div className="mt-4 p-4 rounded-xl bg-red-950/40 border border-red-800/80 text-red-300 flex items-start gap-3">
          <AlertCircle size={18} className="shrink-0 text-red-400 mt-0.5" />
          <div className="text-xs">
            <p className="font-semibold">Invalid YouTube Link</p>
            <p className="mt-0.5 text-red-400">{error}</p>
          </div>
        </div>
      )}

      {/* Identified Video Metadata Card */}
      {metadata && metadata.valid && (
        <div className="mt-6 border border-slate-800 rounded-2xl bg-slate-950/60 overflow-hidden divide-y divide-slate-800">
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
                <a
                  href={metadata.canonical_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-red-400 mt-2 transition-colors"
                >
                  <span>Open Video in Browser</span>
                  <ExternalLink size={12} />
                </a>
              )}
            </div>
          </div>

          {/* Option to Rename Song Title */}
          <div className="p-4 sm:p-5 bg-slate-900/60">
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
                <Edit2 size={13} className="text-indigo-400" />
                <span>Rename Song Title for Analysis & Sheet:</span>
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
              placeholder="e.g. Nallaru Po"
              className="w-full bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded-xl px-3.5 py-2.5 text-sm font-bold text-white focus:outline-none transition-colors"
            />
            <p className="text-[11px] text-slate-400 mt-1.5">
              Customize how the song name will appear on your chord chart, library, and exports.
            </p>
          </div>

          {/* Policy Compliance Notice & Proceed to Audio Upload */}
          <div className="p-4 sm:p-5 bg-amber-950/20 border-t border-amber-900/30">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-3 flex-1">
                <div>
                  <p className="text-xs font-bold text-amber-200 uppercase tracking-wide">
                    Audio Authorization Required
                  </p>
                  <p className="text-xs text-amber-300/90 mt-1 leading-relaxed">
                    Direct stream downloading from YouTube is restricted by copyright and terms of service.
                    Please provide an audio file (<span className="font-mono text-amber-200">MP3, WAV, FLAC, M4A</span>) for this song to begin chord recognition.
                  </p>
                </div>

                <div>
                  <button
                    onClick={() => onSwitchToUpload(customTitle.trim() || metadata.title)}
                    className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 text-xs font-black flex items-center gap-2 shadow-lg shadow-amber-500/20 cursor-pointer transition-all"
                  >
                    <Upload size={15} />
                    <span>Provide Audio File for "{customTitle || metadata.title}"</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
