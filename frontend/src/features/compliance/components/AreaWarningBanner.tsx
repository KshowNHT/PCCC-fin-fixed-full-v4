import React, { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

interface AreaWarningBannerProps {
  warnings: string[];
}

export const AreaWarningBanner: React.FC<AreaWarningBannerProps> = ({ warnings }) => {
  const [expanded, setExpanded] = useState(false);

  if (!warnings || warnings.length === 0) return null;

  return (
    <div className="bg-amber-50/95 border-b border-amber-200/80 px-3 sm:px-4 py-2 text-xs text-amber-900 transition-all shrink-0">
      <div className="flex items-center justify-between gap-2 max-w-5xl mx-auto">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1.5 font-bold cursor-pointer text-left min-w-0 flex-1 hover:text-amber-950"
        >
          <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
          <span className="truncate">
            Lưu ý kỹ thuật ({warnings.length}): {expanded ? "" : warnings[0]}
          </span>
        </button>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg hover:bg-amber-100 text-amber-800 text-[11px] font-semibold shrink-0 cursor-pointer"
        >
          <span>{expanded ? "Thu gọn" : "Xem thêm"}</span>
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {expanded && (
        <ul className="mt-2 space-y-1.5 list-disc list-inside max-w-5xl mx-auto pl-1 text-[11.5px] leading-relaxed border-t border-amber-200/60 pt-2 animate-in fade-in duration-150">
          {warnings.map((w, i) => (
            <li key={`warn-${i}`}>{w}</li>
          ))}
        </ul>
      )}
    </div>
  );
};
