import React, { useState, useRef } from 'react';
import { UploadCloud, FileAudio, ArrowRight } from 'lucide-react';

interface UploadZoneProps {
  onStartAnalysis: (file: File) => void;
  isAnalyzing: boolean;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onStartAnalysis, isAnalyzing }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
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
        <div className="mt-6 p-5 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-between shadow-xl">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
              <FileAudio size={24} />
            </div>
            <div className="text-left">
              <p className="font-semibold text-slate-100 truncate max-w-sm">
                {selectedFile.name}
              </p>
              <p className="text-xs text-slate-400">
                {formatFileSize(selectedFile.size)} • {selectedFile.name.split('.').pop()?.toUpperCase()}
              </p>
            </div>
          </div>

          <button
            onClick={() => onStartAnalysis(selectedFile)}
            disabled={isAnalyzing}
            className="px-6 py-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white font-semibold flex items-center gap-2 shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 cursor-pointer"
          >
            <span>Analyze Song</span>
            <ArrowRight size={18} />
          </button>
        </div>
      )}
    </div>
  );
};
