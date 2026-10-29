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
    <div ref={ref} className="relative inline-block text-left">
      <button
        type="button"
        disabled={disabled || isAnyExporting}
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-200 hover:border-slate-300 text-slate-700 text-xs font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
      >
        {isAnyExporting ? <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-orange shrink-0" /> : <Download className="w-3.5 h-3.5 text-slate-500 shrink-0" />}
        <span className="hidden sm:inline">Xuất báo cáo</span>
        <span className="sm:hidden">Xuất</span>
        <ChevronDown className="w-3.5 h-3.5 text-slate-400 shrink-0" />
      </button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-48 bg-white rounded-xl shadow-xl border border-slate-100 py-1.5 z-50 animate-in fade-in zoom-in-95 duration-150">
          <button
            type="button"
            onClick={() => { onExportDocx(); setOpen(false); }}
            className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 font-medium cursor-pointer"
          >
            <FileText className="w-4 h-4 text-blue-600" />
            <span>Biên bản thẩm duyệt (.docx)</span>
          </button>
          <button
            type="button"
            onClick={() => { onExportPdf(); setOpen(false); }}
            className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 font-medium cursor-pointer"
          >
            <FileSpreadsheet className="w-4 h-4 text-red-600" />
            <span>Bản in thẩm duyệt (.pdf)</span>
          </button>
          <button
            type="button"
            onClick={() => { onExportJson(); setOpen(false); }}
            className="w-full flex items-center gap-2.5 px-3.5 py-2 text-xs text-slate-700 hover:bg-slate-50 font-medium cursor-pointer"
          >
            <Code2 className="w-4 h-4 text-emerald-600" />
            <span>Dữ liệu kiểm tra (.json)</span>
          </button>
        </div>
      )}
    </div>
  );
};

