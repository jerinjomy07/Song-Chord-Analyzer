import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileAudio, ArrowRight, Edit2 } from 'lucide-react';

interface UploadZoneProps {
  onStartAnalysis: (file: File, customTitle?: string) => void;
  isAnalyzing: boolean;
  prefilledTitle?: string;
}

export const UploadZone: React.FC<UploadZoneProps> = ({
  onStartAnalysis,
  isAnalyzing,
  prefilledTitle = '',
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [songTitle, setSongTitle] = useState<string>(prefilledTitle);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (prefilledTitle && !songTitle) {
      setSongTitle(prefilledTitle);
    }
  }, [prefilledTitle]);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (isValidAudio(file.name)) {
        setSelectedFile(file);
        if (!songTitle) {
          setSongTitle(file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
        }
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!songTitle) {
        setSongTitle(file.name.replace(/\.[^/.]+$/, '').replace(/_/g, ' '));
      }
    }
  };

  const isValidAudio = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    return ['mp3', 'wav', 'flac', 'm4a', 'aac', 'ogg', 'wma'].includes(ext || '');
  };

  const formatFileSize = (bytes: number) => {
    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
  };

  return (
    <div className="max-w-2xl mx-auto w-full">
      <div 
        className={`border-2 border-dashed rounded-2xl p-10 text-center transition-all duration-200 cursor-pointer ${
          dragActive 
            ? 'border-indigo-500 bg-indigo-950/20' 
            : 'border-slate-700 bg-slate-900/60 hover:border-slate-500'
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          accept=".mp3,.wav,.flac,.m4a,.aac,.ogg,.wma" 
          className="hidden" 
          onChange={handleChange}
        />

        <div className="flex justify-center mb-4">
          <div className="w-16 h-16 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <UploadCloud size={32} />
          </div>
        </div>

        <h3 className="text-xl font-semibold text-slate-100 mb-1">
          Drop your music file here
        </h3>
        <p className="text-slate-400 text-sm mb-6">
          or click to browse from local storage
        </p>

        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-slate-300 text-xs font-medium">
          <span>Supported: MP3 • WAV • FLAC • M4A • AAC • OGG • WMA</span>
        </div>
      </div>

      {selectedFile && (
        <div className="mt-6 p-5 rounded-2xl bg-slate-900 border border-slate-800 shadow-xl space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 shrink-0">
                <FileAudio size={24} />
              </div>
              <div className="text-left min-w-0">
                <p className="font-semibold text-slate-100 truncate max-w-xs sm:max-w-sm" title={selectedFile.name}>
                  {selectedFile.name}
                </p>
                <p className="text-xs text-slate-400">
                  {formatFileSize(selectedFile.size)} • {selectedFile.name.split('.').pop()?.toUpperCase()}
                </p>
              </div>
            </div>

            <button
              onClick={() => onStartAnalysis(selectedFile, songTitle.trim() || undefined)}
              disabled={isAnalyzing}
              className="px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-bold flex items-center justify-center gap-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 cursor-pointer shrink-0"
            >
              <span>Analyze Song</span>
              <ArrowRight size={18} />
            </button>
          </div>

          {/* Option to Rename the Title of the Song */}
          <div className="pt-3 border-t border-slate-800 text-left">
            <label className="text-xs font-bold text-slate-300 flex items-center gap-1.5 mb-1.5">
              <Edit2 size={13} className="text-indigo-400" />
              <span>Song Title (Editable):</span>
            </label>
            <input
              type="text"
              value={songTitle}
              onChange={(e) => setSongTitle(e.target.value)}
              placeholder="e.g. Nallaru Po"
              className="w-full bg-slate-950 border border-slate-700 focus:border-indigo-500 rounded-xl px-3.5 py-2.5 text-sm font-bold text-white focus:outline-none transition-colors"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Customize the title that will appear on the chord sheet, PDF, and saved library entry.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
