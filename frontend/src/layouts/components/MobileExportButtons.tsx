import React from "react";
import { FileText, FileSpreadsheet, Code2, Loader2 } from "lucide-react";

export interface MobileExportButtonsProps {
  onExportDocx: () => void;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingDocx: boolean;
  isExportingPdf: boolean;
  isExportingJson: boolean;
  disabled: boolean;
  onClose: () => void;
}

export const MobileExportButtons: React.FC<MobileExportButtonsProps> = ({
  onExportDocx,
  onExportPdf,
  onExportJson,
  isExportingDocx,
  isExportingPdf,
  isExportingJson,
  disabled,
  onClose,
}) => {
  const isAnyExporting = isExportingDocx || isExportingPdf || isExportingJson;
  const isBlocked = disabled || isAnyExporting;

  return (
    <div className="grid grid-cols-3 gap-2">
      <button
        type="button"
        disabled={isBlocked}
        onClick={() => { onExportDocx(); onClose(); }}
        className="flex flex-col items-center justify-center gap-1.5 p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-blue-300 dark:hover:border-blue-600 text-slate-700 dark:text-slate-200 font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
      >
        {isExportingDocx ? <Loader2 className="w-4 h-4 animate-spin text-blue-600" /> : <FileText className="w-4 h-4 text-blue-600" />}
        <span className="text-[11px]">Xuất Word</span>
      </button>

      <button
        type="button"
        disabled={isBlocked}
        onClick={() => { onExportPdf(); onClose(); }}
        className="flex flex-col items-center justify-center gap-1.5 p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-red-300 dark:hover:border-red-600 text-slate-700 dark:text-slate-200 font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
      >
        {isExportingPdf ? <Loader2 className="w-4 h-4 animate-spin text-red-600" /> : <FileSpreadsheet className="w-4 h-4 text-red-600" />}
        <span className="text-[11px]">Xuất PDF</span>
      </button>

      <button
        type="button"
        disabled={isBlocked}
        onClick={() => { onExportJson(); onClose(); }}
        className="flex flex-col items-center justify-center gap-1.5 p-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-emerald-300 dark:hover:border-emerald-600 text-slate-700 dark:text-slate-200 font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
      >
        {isExportingJson ? <Loader2 className="w-4 h-4 animate-spin text-emerald-600" /> : <Code2 className="w-4 h-4 text-emerald-600" />}
        <span className="text-[11px]">Xuất JSON</span>
      </button>
    </div>
  );
};

