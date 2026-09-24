import React, { useState } from 'react';
import { FileDown, FileText, Code2, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

interface ExportToolbarProps {
  analysisId: string;
}

export const ExportToolbar: React.FC<ExportToolbarProps> = ({ analysisId }) => {
  const [downloadingFormat, setDownloadingFormat] = useState<'pdf' | 'txt' | 'json' | null>(null);
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  const showToast = (type: 'success' | 'error', message: string) => {
    setToast({ type, message });
    setTimeout(() => {
      setToast(null);
    }, 4500);
  };

  const blobToBase64 = (blob: Blob): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = (reader.result as string).split(',')[1] || '';
        resolve(base64String);
      };
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  const downloadExport = async (format: 'pdf' | 'txt' | 'json') => {
    setDownloadingFormat(format);
    try {
      const res = await fetch(`/api/analysis/${analysisId}/export/${format}`);
      if (!res.ok) {
        throw new Error(`Export request failed: ${res.status} ${res.statusText}`);
      }

      // Extract filename from Content-Disposition header
      let defaultFilename = `Song_ChordSheet.${format}`;
      if (format === 'json') defaultFilename = 'Song_Analysis.json';

      const disposition = res.headers.get('content-disposition');
      if (disposition) {
        const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
        if (utf8Match && utf8Match[1]) {
          defaultFilename = decodeURIComponent(utf8Match[1]);
        } else {
          const asciiMatch = disposition.match(/filename="?([^";]+)"?/i);
          if (asciiMatch && asciiMatch[1]) {
            defaultFilename = asciiMatch[1];
          }
        }
      }

      // 1. Electron Desktop Native Save Dialog Workflow
      if (window.desktopAPI?.saveExportFile) {
        let content: string;
        let isBase64 = false;

        if (format === 'pdf') {
          const blob = await res.blob();
          content = await blobToBase64(blob);
          isBase64 = true;
        } else {
          content = await res.text();
        }

        const result = await window.desktopAPI.saveExportFile({
          defaultFilename,
          format,
          content,
          isBase64
        });

        if (result.canceled) {
          // Graceful user cancellation - no error thrown
          return;
        }

        if (result.success) {
          showToast('success', `Saved ${result.filename || defaultFilename}`);
        } else {
          showToast('error', `${format.toUpperCase()} export failed. Please try again.`);
        }
        return;
      }

      // 2. Web Browser Fallback Workflow
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = defaultFilename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
      showToast('success', `Downloaded ${defaultFilename}`);
    } catch (err: any) {
      console.error(`[Export Error] Failed to export ${format}:`, err);
      showToast('error', `${format.toUpperCase()} export failed. Please try again.`);
    } finally {
      setDownloadingFormat(null);
    }
  };

  return (
    <div className="relative flex flex-wrap items-center gap-2">
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

      {/* Floating Status Notification Toast */}
      {toast && (
        <div
          className={`absolute right-0 -bottom-10 z-50 flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium shadow-lg animate-in fade-in slide-in-from-top-2 duration-200 border whitespace-nowrap ${
            toast.type === 'success'
              ? 'bg-emerald-950/95 text-emerald-200 border-emerald-700/60'
              : 'bg-red-950/95 text-red-200 border-red-700/60'
          }`}
        >
          {toast.type === 'success' ? (
            <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle size={14} className="text-red-400 shrink-0" />
          )}
          <span>{toast.message}</span>
        </div>
      )}
    </div>
  );
};
