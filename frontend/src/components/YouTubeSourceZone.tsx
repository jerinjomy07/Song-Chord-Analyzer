import React, { useState } from 'react';
import { Search, AlertCircle, Upload, Loader2, ExternalLink } from 'lucide-react';

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

export const YouTubeSourceZone: React.FC<YouTubeSourceZoneProps> = ({ onSwitchToUpload }) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<YouTubeMetadata | null>(null);

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

  return (
    <div className="w-full max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-red-600/20 border border-red-500/30 flex items-center justify-center text-red-400">
          <YoutubeIcon size={22} />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">YouTube Link Inspection</h3>
          <p className="text-xs text-slate-400">
            Paste a public YouTube link to inspect video details and check audio authorization.
          </p>
        </div>
      </div>

      {/* URL Input Form */}
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
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-red-500 font-mono transition-colors"
            />
            {url && (
              <button
                type="button"
                onClick={() => setUrl('')}
                className="absolute right-3 top-3 text-slate-500 hover:text-slate-300 text-xs font-semibold cursor-pointer"
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
              <h4 className="text-sm sm:text-base font-bold text-white line-clamp-2">
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

          {/* Policy Compliance Notice & Authorized Upload Fallback */}
          <div className="p-4 sm:p-5 bg-amber-950/20 border-t border-amber-900/30">
            <div className="flex items-start gap-3">
              <AlertCircle size={20} className="text-amber-400 shrink-0 mt-0.5" />
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-bold text-amber-200 uppercase tracking-wide">
                    Policy Notice: Audio Extraction Unavailable
                  </p>
                  <p className="text-xs text-amber-300/90 mt-1 leading-relaxed">
                    This YouTube video cannot be imported directly for audio analysis. Please upload an audio file you are authorized to analyze.
                  </p>
                </div>

                <div>
                  <button
                    onClick={() => onSwitchToUpload(metadata.title)}
                    className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-slate-950 text-xs font-black flex items-center gap-2 shadow-lg shadow-amber-500/20 cursor-pointer transition-all"
                  >
                    <Upload size={15} />
                    <span>Upload Audio Instead</span>
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
