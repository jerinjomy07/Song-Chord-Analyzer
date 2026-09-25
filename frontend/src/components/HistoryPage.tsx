import React, { useState, useEffect, useCallback } from 'react';
import type { HistorySong } from '../types';
import {
  Search,
  Star,
  Clock,
  Music,
  Activity,
  Sliders,
  FolderOpen,
  Edit2,
  Copy,
  RotateCcw,
  Trash2,
  AlertTriangle,
  Loader2,
  Check,
  X,
  FileAudio,
  ExternalLink
} from 'lucide-react';

const YoutubeIcon: React.FC<{ size?: number; className?: string }> = ({ size = 14, className = "" }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className}>
    <path d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>
  </svg>
);

interface HistoryPageProps {
  onOpenSong: (songId: string) => void;
  onNavigateHome: () => void;
  onStartReanalyze?: (songId: string) => void;
}

export const HistoryPage: React.FC<HistoryPageProps> = ({
  onOpenSong,
  onNavigateHome,
  onStartReanalyze,
}) => {
  const [songs, setSongs] = useState<HistorySong[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'last_opened' | 'recently_analyzed' | 'recently_modified' | 'title'>('last_opened');
  const [favoritesOnly, setFavoritesOnly] = useState(false);

  // Modals state
  const [renameTarget, setRenameTarget] = useState<HistorySong | null>(null);
  const [renameTitle, setRenameTitle] = useState('');
  const [isRenaming, setIsRenaming] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<HistorySong | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const [reanalyzeTarget, setReanalyzeTarget] = useState<HistorySong | null>(null);

  const [openingSongId, setOpeningSongId] = useState<string | null>(null);
  const [duplicatingSongId, setDuplicatingSongId] = useState<string | null>(null);

  const fetchSongs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchQuery.trim()) params.append('query', searchQuery.trim());
      params.append('sort_by', sortBy);
      if (favoritesOnly) params.append('favorites_only', 'true');

      const res = await fetch(`/api/history?${params.toString()}`);
      if (res.ok) {
        const data: HistorySong[] = await res.json();
        setSongs(data);
      }
    } catch (err) {
      console.error('Failed to fetch history songs:', err);
    } finally {
      setLoading(false);
    }
  }, [searchQuery, sortBy, favoritesOnly]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSongs();
    }, 200);
    return () => clearTimeout(timer);
  }, [fetchSongs]);

  const handleToggleFavorite = async (e: React.MouseEvent, songId: string) => {
    e.stopPropagation();
    try {
      const res = await fetch(`/api/history/${songId}/favorite`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSongs(prev =>
          prev.map(s => (s.id === songId ? { ...s, is_favorite: data.is_favorite ? 1 : 0 } : s))
        );
      }
    } catch (err) {
      console.error('Failed to toggle favorite:', err);
    }
  };

  const handleOpen = (songId: string) => {
    setOpeningSongId(songId);
    onOpenSong(songId);
  };

  const handleDuplicate = async (e: React.MouseEvent, songId: string) => {
    e.stopPropagation();
    setDuplicatingSongId(songId);
    try {
      const res = await fetch(`/api/history/${songId}/duplicate`, { method: 'POST' });
      if (res.ok) {
        await fetchSongs();
      }
    } catch (err) {
      console.error('Failed to duplicate song:', err);
    } finally {
      setDuplicatingSongId(null);
    }
  };

  const handleSaveRename = async () => {
    if (!renameTarget || !renameTitle.trim()) return;
    setIsRenaming(true);
    try {
      const res = await fetch(`/api/history/${renameTarget.id}/rename`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: renameTitle.trim() }),
      });
      if (res.ok) {
        setSongs(prev =>
          prev.map(s => (s.id === renameTarget.id ? { ...s, title: renameTitle.trim() } : s))
        );
        setRenameTarget(null);
      }
    } catch (err) {
      console.error('Failed to rename song:', err);
    } finally {
      setIsRenaming(false);
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;
    setIsDeleting(true);
    try {
      const res = await fetch(`/api/history/${deleteTarget.id}`, { method: 'DELETE' });
      if (res.ok) {
        setSongs(prev => prev.filter(s => s.id !== deleteTarget.id));
        setDeleteTarget(null);
      }
    } catch (err) {
      console.error('Failed to delete song:', err);
    } finally {
      setIsDeleting(false);
    }
  };

  const handleConfirmReanalyze = () => {
    if (!reanalyzeTarget) return;
    const songId = reanalyzeTarget.id;
    setReanalyzeTarget(null);
    if (onStartReanalyze) {
      onStartReanalyze(songId);
    } else {
      onOpenSong(songId);
    }
  };

  const formatDuration = (secs: number) => {
    if (!secs) return '0:00';
    const mins = Math.floor(secs / 60);
    const rem = Math.floor(secs % 60);
    return `${mins}:${rem < 10 ? '0' : ''}${rem}`;
  };

  const formatDate = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="py-4">
      {/* Top Header & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Song Library & History
          </h2>
          <p className="text-slate-400 text-xs sm:text-sm mt-1">
            Access, play, transpose, and re-export your previously analyzed songs instantly without re-processing.
          </p>
        </div>

        <button
          onClick={onNavigateHome}
          className="self-start md:self-auto px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold transition-all shadow-md shadow-indigo-600/30 flex items-center gap-2 cursor-pointer"
        >
          <Music size={15} />
          <span>+ Analyze New Song</span>
        </button>
      </div>

      {/* Filter & Search Bar */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 mb-6 shadow-xl flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search by song title, filename, or key..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-9 py-2.5 bg-slate-950/80 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-200"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Filter Controls */}
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {/* Favorites Filter Toggle */}
          <button
            onClick={() => setFavoritesOnly(!favoritesOnly)}
            className={`px-3 py-2.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 border transition-all cursor-pointer ${
              favoritesOnly
                ? 'bg-amber-500/20 border-amber-500/40 text-amber-300'
                : 'bg-slate-950/80 border-slate-800 text-slate-400 hover:text-slate-200'
            }`}
            title="Toggle favorites filter"
          >
            <Star size={14} className={favoritesOnly ? 'fill-amber-400 text-amber-400' : ''} />
            <span>Favorites</span>
          </button>

          {/* Sort By Dropdown */}
          <div className="flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 rounded-xl px-3 py-1.5">
            <span className="text-[11px] text-slate-500 font-medium">Sort:</span>
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as any)}
              className="bg-transparent text-xs text-slate-200 font-semibold focus:outline-none cursor-pointer"
            >
              <option value="last_opened" className="bg-slate-900 text-slate-200">Recently Opened</option>
              <option value="recently_analyzed" className="bg-slate-900 text-slate-200">Recently Analyzed</option>
              <option value="recently_modified" className="bg-slate-900 text-slate-200">Recently Modified</option>
              <option value="title" className="bg-slate-900 text-slate-200">Title (A-Z)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Content State: Loading, Empty, or Songs List */}
      {loading ? (
        <div className="py-24 flex flex-col items-center justify-center text-slate-400 gap-3">
          <Loader2 size={32} className="animate-spin text-indigo-500" />
          <p className="text-sm font-medium">Loading your song library...</p>
        </div>
      ) : songs.length === 0 ? (
        <div className="py-20 px-4 bg-slate-900/40 border border-slate-800/80 rounded-2xl text-center max-w-lg mx-auto">
          <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mx-auto mb-4 border border-indigo-500/20">
            <FileAudio size={26} />
          </div>
          {searchQuery || favoritesOnly ? (
            <>
              <h3 className="text-lg font-bold text-white mb-2">No matching songs found</h3>
              <p className="text-xs sm:text-sm text-slate-400 mb-6">
                Try refining your search keyword or clearing the favorites filter.
              </p>
              <button
                onClick={() => {
                  setSearchQuery('');
                  setFavoritesOnly(false);
                }}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold cursor-pointer transition-all"
              >
                Clear Filters
              </button>
            </>
          ) : (
            <>
              <h3 className="text-lg font-bold text-white mb-2">No analyzed songs yet</h3>
              <p className="text-xs sm:text-sm text-slate-400 mb-6 leading-relaxed">
                Analyze your first song and it will automatically be saved to your library for instant offline access and playback.
              </p>
              <button
                onClick={onNavigateHome}
                className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-lg shadow-indigo-600/30 cursor-pointer transition-all inline-flex items-center gap-2"
              >
                <Music size={15} />
                <span>Analyze Your First Song</span>
              </button>
            </>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {songs.map(song => {
            const isFav = Boolean(song.is_favorite);
            const isOpening = openingSongId === song.id;
            const isDuplicating = duplicatingSongId === song.id;

            return (
              <div
                key={song.id}
                onClick={() => handleOpen(song.id)}
                className="group relative bg-slate-900/80 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl p-5 shadow-lg transition-all duration-200 flex flex-col justify-between cursor-pointer"
              >
                {/* Top Row: Title, Fav Star, Badges */}
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        {song.source_type === 'youtube_reference' ? (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-red-500/10 text-red-300 border border-red-500/20 flex items-center gap-1">
                            <YoutubeIcon size={12} className="text-red-400" />
                            <span>YouTube Ref</span>
                          </span>
                        ) : (
                          <span className="uppercase text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                            {song.format || 'AUDIO'}
                          </span>
                        )}
                        {song.audio_available === false && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center gap-1" title="Local audio file not found on disk">
                            <AlertTriangle size={11} className="text-amber-400" />
                            <span>Audio Offline</span>
                          </span>
                        )}
                        {song.edit_count > 0 && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-500/10 text-amber-300 border border-amber-500/20">
                            {song.edit_count} {song.edit_count === 1 ? 'edit' : 'edits'}
                          </span>
                        )}
                        {song.transpose_value !== 0 && (
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                            {song.transpose_value > 0 ? `+${song.transpose_value}` : song.transpose_value} st
                          </span>
                        )}
                      </div>

                      <h3
                        className="text-base sm:text-lg font-bold text-white group-hover:text-indigo-300 transition-colors truncate"
                        title={song.title}
                      >
                        {song.title}
                      </h3>
                      <p className="text-[11px] text-slate-500 truncate" title={song.original_filename}>
                        {song.original_filename}
                      </p>
                      {song.youtube_url && (
                        <a
                          href={song.youtube_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={e => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-[11px] text-red-400/80 hover:text-red-300 transition-colors mt-0.5"
                          title="Open YouTube video in browser"
                        >
                          <span>{song.youtube_channel ? `${song.youtube_channel} • ` : ''}Watch on YouTube</span>
                          <ExternalLink size={10} />
                        </a>
                      )}
                    </div>

                    <button
                      onClick={e => handleToggleFavorite(e, song.id)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 transition-colors shrink-0"
                      title={isFav ? 'Remove from favorites' : 'Add to favorites'}
                    >
                      <Star
                        size={18}
                        className={isFav ? 'fill-amber-400 text-amber-400' : 'text-slate-500 hover:text-amber-400'}
                      />
                    </button>
                  </div>

                  {/* Musical Metrics Badges */}
                  <div className="grid grid-cols-4 gap-2 my-3 py-2.5 px-3 bg-slate-950/60 rounded-xl border border-slate-800/60">
                    <div className="flex items-center gap-1.5">
                      <Music size={13} className="text-indigo-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-[9px] text-slate-500 uppercase font-semibold">Key</span>
                        <span className="block text-xs font-bold text-slate-200 truncate">{song.key_display || '—'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Activity size={13} className="text-amber-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-[9px] text-slate-500 uppercase font-semibold">Tempo</span>
                        <span className="block text-xs font-bold text-slate-200 truncate">{song.bpm ? `${song.bpm} BPM` : '—'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Sliders size={13} className="text-emerald-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-[9px] text-slate-500 uppercase font-semibold">Meter</span>
                        <span className="block text-xs font-bold text-slate-200 truncate">{song.time_signature || '4/4'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Clock size={13} className="text-cyan-400 shrink-0" />
                      <div className="min-w-0">
                        <span className="block text-[9px] text-slate-500 uppercase font-semibold">Length</span>
                        <span className="block text-xs font-bold text-slate-200 truncate">{formatDuration(song.duration)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bottom Row: Date & Action Buttons */}
                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2 mt-1">
                  <span className="text-[11px] text-slate-500">
                    Analyzed {formatDate(song.created_at)}
                  </span>

                  <div className="flex items-center gap-1" onClick={e => e.stopPropagation()}>
                    {/* Primary Open Button */}
                    <button
                      onClick={() => handleOpen(song.id)}
                      disabled={isOpening}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 shadow-sm transition-all cursor-pointer"
                      title="Open chord sheet and player"
                    >
                      {isOpening ? <Loader2 size={13} className="animate-spin" /> : <FolderOpen size={13} />}
                      <span>Open</span>
                    </button>

                    {/* Rename Button */}
                    <button
                      onClick={() => {
                        setRenameTarget(song);
                        setRenameTitle(song.title);
                      }}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      title="Rename song"
                    >
                      <Edit2 size={14} />
                    </button>

                    {/* Duplicate Button */}
                    <button
                      onClick={e => handleDuplicate(e, song.id)}
                      disabled={isDuplicating}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
                      title="Duplicate analysis entry"
                    >
                      {isDuplicating ? <Loader2 size={14} className="animate-spin text-indigo-400" /> : <Copy size={14} />}
                    </button>

                    {/* Re-analyze Button */}
                    <button
                      onClick={() => setReanalyzeTarget(song)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-slate-800 transition-colors"
                      title="Re-run audio analysis"
                    >
                      <RotateCcw size={14} />
                    </button>

                    {/* Delete Button */}
                    <button
                      onClick={() => setDeleteTarget(song)}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
                      title="Delete from library"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* RENAME MODAL */}
      {renameTarget && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <h3 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
              <Edit2 size={18} className="text-indigo-400" />
              <span>Rename Song</span>
            </h3>
            <p className="text-xs text-slate-400 mb-4">
              Enter a new title for this song. This will update all exports and library listings.
            </p>
            <input
              type="text"
              value={renameTitle}
              onChange={e => setRenameTitle(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveRename()}
              autoFocus
              className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-sm text-slate-100 focus:outline-none focus:border-indigo-500 mb-6"
            />
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setRenameTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveRename}
                disabled={isRenaming || !renameTitle.trim()}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-md shadow-indigo-600/30"
              >
                {isRenaming ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                <span>Save Title</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* DELETE MODAL */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-red-900/50 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 text-red-400 flex items-center justify-center mb-4 border border-red-500/20">
              <Trash2 size={22} />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Delete Song from Library?</h3>
            <p className="text-xs text-slate-300 mb-4 leading-relaxed">
              Are you sure you want to delete <span className="text-white font-semibold">"{deleteTarget.title}"</span>?
              This will remove the saved chord analysis, manual edits, and application library files.
              Your original audio file on your computer will not be touched.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 rounded-xl bg-red-600 hover:bg-red-500 disabled:opacity-50 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-md shadow-red-600/30"
              >
                {isDeleting ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}
                <span>Delete Forever</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RE-ANALYZE CONFIRMATION MODAL */}
      {reanalyzeTarget && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-amber-900/50 rounded-2xl p-6 max-w-md w-full shadow-2xl animate-in fade-in zoom-in-95 duration-150">
            <div className="w-12 h-12 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center mb-4 border border-amber-500/20">
              <AlertTriangle size={22} />
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Re-analyze "{reanalyzeTarget.title}"?</h3>
            <p className="text-xs text-slate-300 mb-4 leading-relaxed">
              This will re-run harmonic tempo estimation, meter & downbeat detection, and BTC neural chord recognition on this song using the latest music engine. Any manual chord edits will be refreshed.
            </p>
            <div className="flex items-center justify-end gap-2">
              <button
                onClick={() => setReanalyzeTarget(null)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-300 hover:bg-slate-800 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirmReanalyze}
                className="px-4 py-2 rounded-xl bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-1.5 cursor-pointer shadow-md shadow-amber-600/30"
              >
                <RotateCcw size={13} />
                <span>Re-analyze Audio</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
