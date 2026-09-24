import React, { useState, useEffect, useRef } from 'react';
import { AlertCircle, Edit2, Check, Music, Terminal, FileText, Search, Sparkles, ArrowDownToLine } from 'lucide-react';
import type { SongAnalysis, MusicalSection, ChordPrediction, Bar } from '../types';

interface ChordSheetProps {
  analysis: SongAnalysis;
  onSelectChord: (chord: ChordPrediction, index: number) => void;
  onRenameSection: (sectionId: string, newName: string) => void;
  currentTime: number;
  isPlaying?: boolean;
  onSeek?: (timeSec: number) => void;
}

export const ChordSheet: React.FC<ChordSheetProps> = ({
  analysis,
  onSelectChord,
  onRenameSection,
  currentTime,
  isPlaying = false,
  onSeek,
}) => {
  const [activeTab, setActiveTab] = useState<'sheet' | 'debug'>('sheet');
  const [editingSectionId, setEditingSectionId] = useState<string | null>(null);
  const [tempSectionName, setTempSectionName] = useState("");
  const [debugSearch, setDebugSearch] = useState("");

  // Auto-scroll state (default ON per requirements)
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const [userHasScrolled, setUserHasScrolled] = useState<boolean>(false);
  const isAutoScrollingRef = useRef<boolean>(false);
  const lastScrolledBarRef = useRef<number | null>(null);
  const barRefs = useRef<{ [barNumber: number]: HTMLDivElement | null }>({});

  const startRename = (sec: MusicalSection) => {
    setEditingSectionId(sec.section_id);
    setTempSectionName(sec.name);
  };

  const submitRename = (secId: string) => {
    if (tempSectionName.trim()) {
      onRenameSection(secId, tempSectionName.trim());
    }
    setEditingSectionId(null);
  };

  const getGlobalChordIndex = (chord: ChordPrediction) => {
    return analysis.chords.findIndex(c => c.start_time === chord.start_time);
  };

  // Helper to chunk bars into rows of N bars (4 on desktop, 2 on small screens)
  const chunkBars = (bars: Bar[], chunkSize: number = 4): Bar[][] => {
    const rows: Bar[][] = [];
    for (let i = 0; i < bars.length; i += chunkSize) {
      rows.push(bars.slice(i, i + chunkSize));
    }
    return rows;
  };

  // Detect manual user scrolling during playback without fighting them
  useEffect(() => {
    const handleManualScroll = () => {
      if (!isAutoScrollingRef.current && isPlaying && autoScroll) {
        setUserHasScrolled(true);
      }
    };

    window.addEventListener('wheel', handleManualScroll, { passive: true });
    window.addEventListener('touchmove', handleManualScroll, { passive: true });

    return () => {
      window.removeEventListener('wheel', handleManualScroll);
      window.removeEventListener('touchmove', handleManualScroll);
    };
  }, [isPlaying, autoScroll]);

  // Find currently active bar
  let currentActiveBarNumber: number | null = null;
  for (const sec of analysis.sections) {
    const b = sec.bars.find(bar => currentTime >= bar.start_time && currentTime <= bar.end_time);
    if (b) {
      currentActiveBarNumber = b.bar_number;
      break;
    }
  }

  const scrollToBar = (barNum: number) => {
    const el = barRefs.current[barNum];
    if (el) {
      isAutoScrollingRef.current = true;
      el.scrollIntoView({
        behavior: 'smooth',
        block: 'center',
      });
      setTimeout(() => {
        isAutoScrollingRef.current = false;
      }, 400);
    }
  };

  // Auto-scroll effect: triggers only when active bar changes
  useEffect(() => {
    if (!isPlaying || !autoScroll || userHasScrolled || currentActiveBarNumber === null) {
      return;
    }

    if (currentActiveBarNumber !== lastScrolledBarRef.current) {
      lastScrolledBarRef.current = currentActiveBarNumber;
      scrollToBar(currentActiveBarNumber);
    }
  }, [currentActiveBarNumber, isPlaying, autoScroll, userHasScrolled]);

  // Filter debug view entries
  const filteredDebug = (analysis.debug_view || []).filter(entry => {
    if (!debugSearch.trim()) return true;
    const q = debugSearch.toLowerCase();
    return (
      entry.bar_number.toString().includes(q) ||
      entry.final_display.toLowerCase().includes(q) ||
      entry.sounding_bass.toLowerCase().includes(q) ||
      entry.raw_predictions.some(r => r.toLowerCase().includes(q)) ||
      entry.beat_pooled.some(p => p.toLowerCase().includes(q))
    );
  });

  return (
    <div className="relative w-full bg-slate-900 border border-slate-800 rounded-2xl p-5 sm:p-7 shadow-2xl">
      {/* Top Header, Auto-Scroll Controls & View Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-slate-800 pb-3 mb-5 gap-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Music size={20} className="text-indigo-400" />
            <span className="tracking-wide">CHORD SHEET</span>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 border border-indigo-800/50">
              {analysis.meter.display} • {Math.round(analysis.tempo.bpm)} BPM
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Musician bar-based chord chart. Click any bar or chord to jump playback and edit.
          </p>
        </div>

        {/* Tab Switcher & Auto-Scroll Toggle */}
        <div className="flex items-center gap-2 flex-wrap">
          {/* Auto Scroll Toggle Button */}
          <button
            onClick={() => {
              const nextState = !autoScroll;
              setAutoScroll(nextState);
              if (nextState) {
                setUserHasScrolled(false);
                if (currentActiveBarNumber !== null) {
                  scrollToBar(currentActiveBarNumber);
                }
              }
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
              autoScroll
                ? 'bg-emerald-950/70 text-emerald-300 border-emerald-700/60 shadow-sm'
                : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
            }`}
            title={autoScroll ? "Auto-scroll is following playback (click to disable)" : "Auto-scroll is paused (click to enable)"}
          >
            <ArrowDownToLine size={14} className={autoScroll ? "text-emerald-400" : "text-slate-500"} />
            <span>Auto Scroll {autoScroll ? '✓' : 'OFF'}</span>
          </button>

          {/* Lead Sheet / Debug View */}
          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('sheet')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'sheet'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <FileText size={14} />
              <span>Lead Sheet</span>
            </button>

            <button
              onClick={() => setActiveTab('debug')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                activeTab === 'debug'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Terminal size={14} />
              <span>Debug View</span>
              {analysis.debug_view && (
                <span className="bg-slate-800 text-[10px] text-indigo-300 px-1.5 py-0.2 rounded-full">
                  {analysis.debug_view.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* VIEW 1: Musician Lead Sheet View (Musical Bar-Based Layout) */}
      {activeTab === 'sheet' && (
        <div className="space-y-6">
          {analysis.sections.map((section) => {
            const isSectionActive = currentTime >= section.start_time && currentTime <= section.end_time;
            const barRows = chunkBars(section.bars, 4);

            return (
              <div
                key={section.section_id}
                className={`transition-all rounded-xl p-3 sm:p-4 ${
                  isSectionActive 
                    ? 'bg-indigo-950/30 ring-1 ring-indigo-500/40' 
                    : 'bg-slate-950/40'
                }`}
              >
                {/* Section Header */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    {editingSectionId === section.section_id ? (
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={tempSectionName}
                          onChange={(e) => setTempSectionName(e.target.value)}
                          className="bg-slate-900 border border-indigo-500 rounded px-2 py-0.5 text-xs font-bold text-white uppercase focus:outline-none"
                          autoFocus
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') submitRename(section.section_id);
                            if (e.key === 'Escape') setEditingSectionId(null);
                          }}
                        />
                        <button
                          onClick={() => submitRename(section.section_id)}
                          className="p-1 rounded bg-indigo-600 text-white hover:bg-indigo-500 cursor-pointer"
                        >
                          <Check size={12} />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 group">
                        <span className={`text-xs sm:text-sm font-black tracking-wider uppercase ${
                          isSectionActive ? 'text-indigo-300' : 'text-slate-300'
                        }`}>
                          {section.name}
                        </span>
                        {section.is_repeated && (
                          <span className="text-[10px] font-semibold text-amber-400 bg-amber-950/50 border border-amber-800/40 px-1.5 py-0.2 rounded">
                            Repeat
                          </span>
                        )}
                        <button
                          onClick={() => startRename(section)}
                          className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-300 p-0.5 transition-opacity cursor-pointer"
                          title="Rename section"
                        >
                          <Edit2 size={12} />
                        </button>
                      </div>
                    )}
                  </div>

                  <span className="text-[10px] font-mono text-slate-500">
                    Bars {section.start_bar}–{section.end_bar}
                  </span>
                </div>

                {/* Continuous Connected Bar Rows */}
                <div className="space-y-1.5">
                  {barRows.map((rowBars, rIdx) => (
                    <div
                      key={rIdx}
                      className="flex w-full border-y border-l border-r border-slate-700/80 bg-slate-900/90 rounded-md overflow-hidden"
                    >
                      {rowBars.map((bar) => {
                        const isBarActive = currentTime >= bar.start_time && currentTime <= bar.end_time;
                        const totalBeats = bar.beats || 4;

                        // Check if bar has legitimate chords
                        const validChords = bar.chords.filter(c => c.display !== 'N');
                        const isNoChordBar = validChords.length === 0;

                        return (
                          <div
                            key={bar.bar_number}
                            ref={(el) => {
                              barRefs.current[bar.bar_number] = el;
                            }}
                            onClick={() => {
                              if (onSeek) onSeek(bar.start_time);
                            }}
                            className={`relative flex-1 min-w-0 border-r border-slate-700/80 last:border-r-0 h-11 sm:h-12 flex items-center transition-all px-1 sm:px-2 cursor-pointer select-none ${
                              isBarActive 
                                ? 'bg-indigo-950/80 ring-2 ring-indigo-500/60 shadow-lg z-10' 
                                : 'hover:bg-slate-800/50'
                            }`}
                            title={`Bar ${bar.bar_number} (Click to jump)`}
                          >
                            {/* Subtle Bar Number in top-left */}
                            <span className="absolute top-0.5 left-1 text-[8px] font-mono text-slate-500 pointer-events-none">
                              {bar.bar_number}
                            </span>

                            {isNoChordBar ? (
                              <div className="w-full text-center text-slate-600 font-bold select-none text-xs sm:text-sm">
                                —
                              </div>
                            ) : (
                              /* Beat-positioned chords on single horizontal line */
                              <div className="w-full flex items-center h-full">
                                {bar.chords.map((chord, cIdx) => {
                                  const isChordPlaying = currentTime >= chord.start_time && currentTime <= chord.end_time;
                                  const globalIdx = getGlobalChordIndex(chord);
                                  const chordBeats = chord.beat_duration || (totalBeats / bar.chords.length);
                                  const widthPct = Math.max(15, (chordBeats / totalBeats) * 100);

                                  if (chord.display === 'N') {
                                    return (
                                      <div
                                        key={cIdx}
                                        style={{ width: `${widthPct}%` }}
                                        className="flex items-center justify-center text-slate-600 text-xs font-bold select-none"
                                      >
                                        —
                                      </div>
                                    );
                                  }

                                  return (
                                    <div
                                      key={cIdx}
                                      style={{ width: `${widthPct}%` }}
                                      className="flex items-center pl-0.5 sm:pl-1"
                                    >
                                      {cIdx > 0 && (
                                        <span className="text-slate-500 font-bold text-xs select-none pr-1">/</span>
                                      )}
                                      <button
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          if (onSeek) onSeek(chord.start_time);
                                          onSelectChord(chord, globalIdx);
                                        }}
                                        className={`group relative inline-flex items-center px-1.5 sm:px-2 py-0.5 sm:py-1 rounded text-xs sm:text-sm font-extrabold tracking-tight transition-all cursor-pointer ${
                                          isChordPlaying
                                            ? 'bg-amber-400 text-slate-950 font-black shadow-lg shadow-amber-400/50 ring-2 ring-amber-300 scale-105 z-20'
                                            : 'text-slate-100 hover:text-indigo-300 hover:bg-slate-800'
                                        }`}
                                        title={`Bar ${bar.bar_number}, Beat ${chord.beat || chord.beat_position || 1}: ${chord.display} (${Math.round(chord.confidence * 100)}% conf - Click to jump)`}
                                      >
                                        <span>{chord.display}</span>

                                        {/* Low-confidence review flag */}
                                        {chord.needs_review && (
                                          <span className="absolute -top-1 -right-1 text-amber-400" title="Review recommended">
                                            <AlertCircle size={9} className="fill-amber-400/20" />
                                          </span>
                                        )}
                                      </button>
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}

                      {/* If the last row has fewer than 4 bars, pad empty visual bars */}
                      {rowBars.length < 4 && (
                        Array.from({ length: 4 - rowBars.length }).map((_, padIdx) => (
                          <div
                            key={`pad-${padIdx}`}
                            className="flex-1 min-w-0 border-r border-slate-700/80 last:border-r-0 h-11 sm:h-12 bg-slate-950/30"
                          />
                        ))
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Floating Follow Playback Button (when user manually scrolled away during playback) */}
      {userHasScrolled && isPlaying && (
        <button
          onClick={() => {
            setUserHasScrolled(false);
            if (currentActiveBarNumber !== null) {
              lastScrolledBarRef.current = currentActiveBarNumber;
              scrollToBar(currentActiveBarNumber);
            }
          }}
          className="fixed bottom-8 right-8 z-50 px-4 py-2.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-extrabold shadow-2xl flex items-center gap-2 animate-bounce cursor-pointer border border-indigo-400/40"
          title="Resume following active playback bar"
        >
          <ArrowDownToLine size={16} />
          <span>Follow Playback</span>
        </button>
      )}

      {/* VIEW 2: Developer / Musician Side-by-Side Debug View */}
      {activeTab === 'debug' && (
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-950 p-4 rounded-xl border border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-1.5">
                <Sparkles size={16} className="text-indigo-400" />
                <span>Bar & Beat Harmonic Debug Inspection</span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Verifies exact Section, Bar Number, Beat assignment, Duration, Detected Chord, Audio Timestamps, and Confidence.
              </p>
            </div>

            {/* Search Filter */}
            <div className="relative">
              <Search size={14} className="absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={debugSearch}
                onChange={(e) => setDebugSearch(e.target.value)}
                placeholder="Filter bar # or chord..."
                className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 w-48 sm:w-60"
              />
            </div>
          </div>

          {/* Section -> Bar -> Beat-level Table */}
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-900/60 text-slate-400 font-semibold">
                  <th className="py-2 px-3 w-16">Bar</th>
                  <th className="py-2 px-3 w-28">Time</th>
                  <th className="py-2 px-3">Chord Events (Beat • Duration • Chord • Conf)</th>
                  <th className="py-2 px-3 w-32">Sounding Bass</th>
                  <th className="py-2 px-3 w-36">Raw Argmax</th>
                  <th className="py-2 px-3 w-32 text-right">Bar Display</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredDebug.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No debug entries found.
                    </td>
                  </tr>
                ) : (
                  filteredDebug.map((entry) => {
                    const isSlash = entry.final_display.includes('/');
                    return (
                      <tr 
                        key={entry.bar_number}
                        className={`hover:bg-slate-900/50 transition-colors ${
                          isSlash ? 'bg-indigo-950/10' : ''
                        }`}
                      >
                        <td className="py-2 px-3 font-bold text-slate-300">
                          Bar {entry.bar_number}
                        </td>
                        <td className="py-2 px-3 text-slate-500 text-[11px]">
                          {entry.time}
                        </td>
                        <td className="py-2 px-3">
                          {entry.chord_events && entry.chord_events.length > 0 ? (
                            <div className="flex flex-wrap gap-2">
                              {entry.chord_events.map((ce, ceIdx) => (
                                <span
                                  key={ceIdx}
                                  className="inline-flex items-center gap-1.5 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-[11px]"
                                >
                                  <span className="text-slate-400 font-semibold">Beat {ce.beat}:</span>
                                  <span className="text-indigo-300 font-bold">{ce.chord}</span>
                                  <span className="text-slate-500 text-[10px]">({ce.beat_duration}b • {Math.round(ce.confidence * 100)}%)</span>
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-slate-400 font-semibold">{entry.musical_result.join(' ')}</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-emerald-400 text-[11px]">
                          {entry.sounding_bass !== "None" ? (
                            <span className="bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.5 rounded">
                              {entry.sounding_bass}
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="py-2 px-3 text-slate-500 text-[11px]">
                          {entry.raw_predictions.join(' • ')}
                        </td>
                        <td className="py-2 px-3 text-right">
                          <span className="font-extrabold text-sm text-indigo-400 bg-indigo-950/70 border border-indigo-800/50 px-2 py-0.5 rounded">
                            | {entry.final_display} |
                          </span>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
