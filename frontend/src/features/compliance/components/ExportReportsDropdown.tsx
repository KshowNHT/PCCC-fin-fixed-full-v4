import React, { useState, useRef, useEffect } from "react";
import { Download, FileText, FileSpreadsheet, Code2, ChevronDown, Loader2 } from "lucide-react";

interface ExportReportsDropdownProps {
  onExportDocx: () => void;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingDocx: boolean;
  isExportingPdf: boolean;
  isExportingJson: boolean;
  disabled?: boolean;
}

export const ExportReportsDropdown: React.FC<ExportReportsDropdownProps> = ({
  onExportDocx,
  onExportPdf,
  onExportJson,
  isExportingDocx,
  isExportingPdf,
  isExportingJson,
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const isAnyExporting = isExportingDocx || isExportingPdf || isExportingJson;

  useEffect(() => {
    const handleOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  return (
    <div ref={ref} className="relative inline-flex items-center gap-1.5" data-testid="report-export-toolbar">
      {/* Desktop / Tablet: 3 nút Xuất Word, Xuất PDF, Xuất JSON */}
      <div className="hidden lg:inline-flex items-center gap-1">
        <button
          id="btn-export-word"
          data-testid="btn-export-word"
          type="button"
          disabled={disabled || isAnyExporting}
          onClick={onExportDocx}
          title="Xuất biên bản thẩm định định dạng Word (.docx)"
          className="inline-flex items-center gap-1 px-1.5 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-blue-300 dark:hover:border-blue-600 text-slate-700 dark:text-slate-200 text-[11px] font-semibold whitespace-nowrap shrink-0 shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          {isExportingDocx ? <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" /> : <FileText className="w-3.5 h-3.5 text-blue-600" />}
          <span>Xuất Word</span>
        </button>

        <button
          id="btn-export-pdf"
          data-testid="btn-export-pdf"
          type="button"
          disabled={disabled || isAnyExporting}
          onClick={onExportPdf}
          title="Xuất bản in báo cáo thẩm định định dạng PDF (.pdf)"
          className="inline-flex items-center gap-1 px-1.5 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-red-300 dark:hover:border-red-600 text-slate-700 dark:text-slate-200 text-[11px] font-semibold whitespace-nowrap shrink-0 shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          {isExportingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin text-red-600" /> : <FileSpreadsheet className="w-3.5 h-3.5 text-red-600" />}
          <span>Xuất PDF</span>
        </button>

        <button
          id="btn-export-json"
          data-testid="btn-export-json"
          type="button"
          disabled={disabled || isAnyExporting}
          onClick={onExportJson}
          title="Xuất dữ liệu thẩm định định dạng JSON (.json)"
          className="inline-flex items-center gap-1 px-1.5 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-emerald-300 dark:hover:border-emerald-600 text-slate-700 dark:text-slate-200 text-[11px] font-semibold whitespace-nowrap shrink-0 shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          {isExportingJson ? <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" /> : <Code2 className="w-3.5 h-3.5 text-emerald-600" />}
          <span>Xuất JSON</span>
        </button>
      </div>

      {/* Mobile / Màn hình hẹp (< lg) */}
      <div className="lg:hidden relative inline-block text-left">
        <button
          type="button"
          disabled={disabled || isAnyExporting}
          onClick={() => setOpen(!open)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:border-slate-300 text-slate-700 dark:text-slate-200 text-xs font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          {isAnyExporting ? <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-orange shrink-0" /> : <Download className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
          <span className="hidden sm:inline">Xuất báo cáo</span>
          <span className="sm:hidden">Xuất</span>
          <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
        </button>

        {open && (
          <div className="absolute right-0 mt-1.5 w-52 bg-white dark:bg-slate-900 rounded-xl shadow-xl border border-slate-100 dark:border-slate-800 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
            <button
              type="button"
              onClick={() => { onExportDocx(); setOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 font-medium cursor-pointer"
            >
              <FileText className="w-4 h-4 text-blue-600" />
              <span>Xuất Word (.docx)</span>
            </button>
            <button
              type="button"
              onClick={() => { onExportPdf(); setOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 font-medium cursor-pointer"
            >
              <FileSpreadsheet className="w-4 h-4 text-red-600" />
              <span>Xuất PDF (.pdf)</span>
            </button>
            <button
              type="button"
              onClick={() => { onExportJson(); setOpen(false); }}
              className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 dark:text-slate-200 hover:bg-slate-50 dark:hover:bg-slate-800 font-medium cursor-pointer"
            >
              <Code2 className="w-4 h-4 text-emerald-600" />
              <span>Xuất JSON (.json)</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
