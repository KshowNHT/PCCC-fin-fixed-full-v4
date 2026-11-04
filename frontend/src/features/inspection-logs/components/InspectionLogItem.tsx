import React from "react";
import { CheckCircle2, ChevronDown, ChevronUp, Clock, XCircle } from "lucide-react";
import { InspectionLogEntry } from "../types";
import { InspectionLogDetail } from "./InspectionLogDetail";

interface InspectionLogItemProps {
  log: InspectionLogEntry;
  isExpanded: boolean;
  onToggleExpand: (id: string) => void;
}

const TRIGGER_LABELS: Record<string, string> = {
  chat: "Trò chuyện AI",
  manual_appraise: "Kích hoạt thẩm định thủ công",
  ocr_autofill: "Tự động điền từ bản vẽ (OCR)",
};

export const InspectionLogItem: React.FC<InspectionLogItemProps> = ({
  log,
  isExpanded,
  onToggleExpand,
}) => {
  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString("vi-VN");
    } catch {
      return iso;
    }
  };

  return (
    <div
      className={`border rounded-xl transition-all duration-200 overflow-hidden ${
        isExpanded
          ? "border-brand-orange/60 shadow-md bg-white"
          : "border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-white"
      }`}
    >
      {/* Clickable Header Row */}
      <div
        onClick={() => onToggleExpand(log.id)}
        className="p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
      >
        <div className="flex items-center gap-3 min-w-0">
          <button
            type="button"
            className="p-1 rounded-md text-slate-400 hover:text-brand-orange transition-colors shrink-0"
            title={isExpanded ? "Thu gọn" : "Bấm để xem chi tiết"}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-brand-orange" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-800 flex items-center gap-1 font-mono">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                {formatDate(log.createdAt)}
              </span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-200/80 text-slate-700">
                {TRIGGER_LABELS[log.triggerSource] || log.triggerSource}
              </span>
            </div>

            <div className="mt-1 flex items-center gap-2">
              {log.appraisalStatus === "required" || log.isSubjectToAppraisal ? (
                <span className="inline-flex items-center gap-1 text-red-600 text-xs font-bold">
                  <XCircle className="w-3.5 h-3.5" /> Thuộc diện thẩm định PCCC
                </span>
              ) : log.appraisalStatus === "not_required" ? (
                <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-bold">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Dưới ngưỡng danh mục thẩm duyệt
                </span>
              ) : (
                <span className="text-amber-700 text-xs font-medium">Cần rà soát / chưa đủ căn cứ</span>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right text-xs">
            <span className="text-emerald-600 font-bold font-mono">{log.compliantCount}</span>
            <span className="text-slate-300 mx-1">/</span>
            <span className="text-rose-600 font-bold font-mono">{log.nonCompliantCount}</span>
            <p className="text-[10px] text-slate-400 font-sans">Đạt / K.Đạt</p>
          </div>
          <span className="text-[11px] text-brand-orange font-semibold hover:underline">
            {isExpanded ? "Thu gọn" : "Xem chi tiết"}
          </span>
        </div>
      </div>

      {/* Expanded Accordion Body */}
      {isExpanded && <InspectionLogDetail log={log} />}
    </div>
  );
};

