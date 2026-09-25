import React, { useState, useEffect } from 'react';
import type { HistorySong } from '../types';
import { History, Music, ArrowRight, Clock, Activity, FolderOpen, Loader2, RotateCcw } from 'lucide-react';

interface RecentSongsSectionProps {
  onOpenSong: (songId: string) => void;
  onNavigateHistory: () => void;
  onReanalyzeSong?: (songId: string) => void;
  refreshTrigger?: number;
}

export const RecentSongsSection: React.FC<RecentSongsSectionProps> = ({
  onOpenSong,
  onNavigateHistory,
  onReanalyzeSong,
  refreshTrigger = 0,
}) => {
  const [recentSongs, setRecentSongs] = useState<HistorySong[]>([]);
  const [loading, setLoading] = useState(true);
  const [openingId, setOpeningId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchRecent = async () => {
      try {
        const res = await fetch('/api/history/recent?limit=4');
        if (res.ok && isMounted) {
          const data: HistorySong[] = await res.json();
          setRecentSongs(data);
        }
      } catch (err) {
        console.error('Failed to fetch recent songs:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchRecent();
    return () => {
      isMounted = false;
    };
  }, [refreshTrigger]);

  if (loading || recentSongs.length === 0) {
    return null;
  }

  const formatDuration = (secs: number) => {
    if (!secs) return '0:00';
    const mins = Math.floor(secs / 60);
    const rem = Math.floor(secs % 60);
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  const handleOpen = (songId: string) => {
    setOpeningId(songId);
    onOpenSong(songId);
  };

  return (
    <div className="mt-12 pt-8 border-t border-slate-800/80">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History size={16} className="text-indigo-400" />
          <h3 className="text-sm font-bold text-white uppercase tracking-wider">Recent Songs</h3>
        </div>
        <button
          onClick={onNavigateHistory}
          className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-colors cursor-pointer"
        >
          <span>View All in Library</span>
          <ArrowRight size={13} />
        </button>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {recentSongs.map(song => {
          const isOpening = openingId === song.id;
          return (
            <div
              key={song.id}
              onClick={() => handleOpen(song.id)}
              className="group bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-xl p-3.5 shadow-md transition-all cursor-pointer flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-1 mb-1.5">
                  <h4
                    className="text-xs font-bold text-slate-100 group-hover:text-indigo-300 transition-colors truncate flex-1"
                    title={song.title}
                  >
                    {song.title}
                  </h4>
                  {song.source_type === 'youtube_reference' ? (
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/20">
                      YT REF
                    </span>
                  ) : (
                    <span className="text-[9px] font-bold uppercase px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                      {song.format || 'AUDIO'}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3 text-[11px] text-slate-400 mb-3">
                  <div className="flex items-center gap-1">
                    <Music size={11} className="text-indigo-400" />
                    <span>{song.key_display || '—'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Activity size={11} className="text-amber-400" />
                    <span>{song.bpm ? `${song.bpm}` : '—'}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <Clock size={11} className="text-cyan-400" />
                    <span>{formatDuration(song.duration)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-1.5 mt-1">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOpen(song.id);
                  }}
                  disabled={isOpening}
                  className="flex-1 py-1.5 px-2 rounded-lg bg-slate-800 hover:bg-indigo-600 disabled:opacity-50 text-slate-200 hover:text-white text-[11px] font-bold flex items-center justify-center gap-1.5 transition-all cursor-pointer"
                >
                  {isOpening ? <Loader2 size={12} className="animate-spin" /> : <FolderOpen size={12} />}
                  <span>Open</span>
                </button>
                {onReanalyzeSong && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onReanalyzeSong(song.id);
                    }}
                    disabled={isOpening}
                    className="py-1.5 px-2.5 rounded-lg bg-slate-800/80 hover:bg-amber-500/20 text-slate-400 hover:text-amber-300 border border-slate-700/60 hover:border-amber-500/40 disabled:opacity-50 text-[11px] font-bold flex items-center justify-center gap-1 transition-all cursor-pointer"
                    title="Re-analyze with latest music engine"
                  >
                    <RotateCcw size={12} className="text-amber-400" />
                    <span>Re-analyze</span>
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
