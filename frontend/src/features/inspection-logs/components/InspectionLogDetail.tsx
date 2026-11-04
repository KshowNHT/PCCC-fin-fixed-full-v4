import React from "react";
import { AlertTriangle, BookOpen, FileCheck2, Layers } from "lucide-react";
import { InspectionLogEntry } from "../types";

interface InspectionLogDetailProps {
  log: InspectionLogEntry;
}

export const InspectionLogDetail: React.FC<InspectionLogDetailProps> = ({ log }) => {
  const nonCompliantItems = (log.checklist || []).filter(
    (c) =>
      c.result === "Không đạt" ||
      c.result === "Khuyến nghị mạnh" ||
      c.result === "Khuyến nghị"
  );
  const basis = log.appraisalBasis || log.checklist?.[0]?.reviewedBasis;

  return (
    <div className="p-4 pt-2 border-t border-slate-150 bg-slate-50/70 space-y-3.5 text-xs">
      {/* 1. Kết luận thẩm định */}
      <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
        <div className="flex items-center gap-1.5 font-bold text-slate-800 mb-1">
          <FileCheck2 className="w-4 h-4 text-brand-orange" />
          <span>Kết luận Thẩm định &amp; Đánh giá:</span>
        </div>
        <p className="text-slate-700 leading-relaxed font-sans">
          {log.appraisalReason || "Chưa ghi nhận lý do thẩm duyệt cụ thể."}
        </p>
      </div>

      {/* 2. Căn cứ pháp lý */}
      {basis && (
        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
          <div className="flex items-center gap-1.5 font-bold text-slate-800 mb-2">
            <BookOpen className="w-4 h-4 text-blue-600" />
            <span>Căn cứ Pháp lý &amp; Quy chuẩn Áp dụng:</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11.5px]">
            {basis.lawDocument && (
              <div className="p-2 bg-slate-50 rounded-lg">
                <span className="text-slate-500 font-medium">Văn bản pháp quy: </span>
                <span className="font-bold text-slate-800">{basis.lawDocument}</span>
              </div>
            )}
            {basis.article && (
              <div className="p-2 bg-slate-50 rounded-lg">
                <span className="text-slate-500 font-medium">Điều khoản: </span>
                <span className="font-bold text-slate-800">{basis.article}</span>
              </div>
            )}
            {basis.thresholdUsed && (
              <div className="p-2 bg-slate-50 rounded-lg sm:col-span-2">
                <span className="text-slate-500 font-medium">Ngưỡng áp dụng: </span>
                <span className="font-bold text-brand-orange">{basis.thresholdUsed}</span>
              </div>
            )}
            {basis.legalExcerpt && (
              <div className="p-2 bg-slate-50 rounded-lg sm:col-span-2 italic text-slate-600">
                &ldquo;{basis.legalExcerpt}&rdquo;
              </div>
            )}
          </div>
        </div>
      )}

      {/* 3. Danh sách cảnh báo kỹ thuật */}
      {log.warnings && log.warnings.length > 0 && (
        <div className="bg-amber-50/80 p-3.5 rounded-xl border border-amber-200 text-amber-900">
          <div className="flex items-center gap-1.5 font-bold text-amber-800 mb-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <span>Lưu ý &amp; Cảnh báo kỹ thuật ({log.warnings.length}):</span>
          </div>
          <ul className="space-y-1 pl-4 list-disc text-[11.5px] leading-relaxed">
            {log.warnings.map((w) => (
              <li key={`${log.id}-w-${w.slice(0, 30)}`}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 4. Hạng mục Chưa đạt trong Checklist */}
      {nonCompliantItems.length > 0 && (
        <div className="bg-rose-50/60 p-3.5 rounded-xl border border-rose-200 text-rose-950">
          <div className="flex items-center gap-1.5 font-bold text-rose-800 mb-1.5">
            <Layers className="w-4 h-4 text-rose-600" />
            <span>Các hạng mục chưa đạt yêu cầu ({nonCompliantItems.length}):</span>
          </div>
          <div className="space-y-1.5">
            {nonCompliantItems.map((item) => (
              <div
                key={`${log.id}-nc-${item.category || ""}-${item.item || ""}`}
                className="bg-white/80 p-2 rounded-lg border border-rose-100 flex items-start justify-between gap-2"
              >
                <div>
                  <p className="font-bold text-slate-800">{item.item || item.category}</p>
                  <p className="text-[11px] text-slate-500">{item.requirement || item.standard}</p>
                  {item.note && <p className="text-[10.5px] text-rose-600 mt-0.5">{item.note}</p>}
                </div>
                <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 shrink-0">
                  {item.result}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

