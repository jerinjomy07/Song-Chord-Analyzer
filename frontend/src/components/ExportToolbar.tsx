import React, { useState } from 'react';
import { FileDown, FileText, Code2, Loader2 } from 'lucide-react';

interface ExportToolbarProps {
  analysisId: string;
}

export const ExportToolbar: React.FC<ExportToolbarProps> = ({ analysisId }) => {
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'txt' | 'json' | null>(null);

  const downloadExport = async (format: 'pdf' | 'txt' | 'json') => {
    setDownloadingFormat(format);
    try {
      const res = await fetch(`/api/analysis/${analysisId}/export/${format}`);
      if (!res.ok) {
        throw new Error(`Export request failed: ${res.status} ${res.statusText}`);
      }

      const blob = await res.blob();
      let filename = `Chords.${format}`;

      const disposition = res.headers.get('content-disposition');
      if (disposition) {
        const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
        if (utf8Match && utf8Match[1]) {
          filename = decodeURIComponent(utf8Match[1]);
        } else {
          const asciiMatch = disposition.match(/filename="?([^";]+)"?/i);
          if (asciiMatch && asciiMatch[1]) {
            filename = asciiMatch[1];
          }
        }
      }

      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.warn('Direct blob download fallback to window.open:', err);
      window.open(`/api/analysis/${analysisId}/export/${format}`, '_blank');
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        onClick={() => downloadExport('pdf')}
        disabled={downloadingFormat !== null}
        className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 text-xs font-semibold flex items-center gap-2 border border-slate-700 shadow-sm transition-all cursor-pointer"
        title="Download printable PDF chord chart"
      >
        {downloadingFormat === 'pdf' ? (
          <Loader2 size={15} className="animate-spin text-red-400" />
        ) : (
          <FileDown size={15} className="text-red-400" />
        )}
        <span>Export PDF</span>
      </button>

      <button
        onClick={() => downloadExport('txt')}
        disabled={downloadingFormat !== null}
        className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 text-xs font-semibold flex items-center gap-2 border border-slate-700 shadow-sm transition-all cursor-pointer"
        title="Download monospace text chart"
      >
        {downloadingFormat === 'txt' ? (
          <Loader2 size={15} className="animate-spin text-amber-400" />
        ) : (
          <FileText size={15} className="text-amber-400" />
        )}
        <span>Export TXT</span>
      </button>

      <button
        onClick={() => downloadExport('json')}
        disabled={downloadingFormat !== null}
        className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-slate-100 text-xs font-semibold flex items-center gap-2 border border-slate-700 shadow-sm transition-all cursor-pointer"
        title="Download structured JSON"
      >
        {downloadingFormat === 'json' ? (
          <Loader2 size={15} className="animate-spin text-emerald-400" />
        ) : (
          <Code2 size={15} className="text-emerald-400" />
        )}
        <span>Export JSON</span>
      </button>
    </div>
  );
};
