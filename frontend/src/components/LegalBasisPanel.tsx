import React from "react";
import { AlertTriangle, CheckCircle, Info, XCircle } from "lucide-react";
import type { AppraisalBasis, AppraisalStatus } from "../types";

/** Displays the backend-approved basis; never derives legal thresholds in the browser. */

const FIELD_LABELS: Record<string, string> = {
  floors: "số tầng nổi",
  totalFloorArea: "tổng diện tích sàn",
  height: "chiều cao PCCC",
  type: "loại công trình / công năng",
};

export function resolveStatus(basis: AppraisalBasis | null | undefined, isSubject: boolean): AppraisalStatus {
  return basis?.status ?? "insufficient_data";
}

export const VERDICT_STYLES: Record<AppraisalStatus, { container: string; icon: string; conclusion: string }> = {
  required: {
    container: "bg-gradient-to-b from-orange-50 to-orange-100 border-orange-355 text-orange-950 shadow-[0_5px_0_0_#EA580C,0_8px_20px_rgba(234,88,12,0.15)]",
    icon: "from-orange-500 to-orange-700 shadow-[0_4px_0_0_#9A3412,0_4px_10px_rgba(0,0,0,0.18)]",
    conclusion: "text-red-750",
  },
  not_required: {
    container: "bg-gradient-to-b from-emerald-50 to-emerald-100 border-emerald-355 text-emerald-950 shadow-[0_5px_0_0_#059669,0_8px_20px_rgba(5,150,105,0.15)]",
    icon: "from-emerald-500 to-emerald-700 shadow-[0_4px_0_0_#047857,0_4px_10px_rgba(0,0,0,0.18)]",
    conclusion: "text-emerald-800",
  },
  insufficient_data: {
    container: "bg-gradient-to-b from-amber-50 to-amber-100 border-amber-300 text-amber-950 shadow-[0_5px_0_0_#B45309,0_8px_20px_rgba(180,83,9,0.15)]",
    icon: "from-amber-500 to-amber-700 shadow-[0_4px_0_0_#78350F,0_4px_10px_rgba(0,0,0,0.18)]",
    conclusion: "text-amber-800",
  },
};

export function verdictHeading(status: AppraisalStatus, basis?: AppraisalBasis | null): string {
  if (status === "required") return "THUỘC DIỆN THẨM ĐỊNH THIẾT KẾ VỀ PCCC";
  if (status === "insufficient_data") return "CẦN BỔ SUNG DỮ LIỆU / XÁC NHẬN PHÂN LOẠI";
  // Chỉ nhóm có ngưỡng pháp định mới được khẳng định "không thuộc diện".
  if (basis && basis.thresholdSource !== "statutory") {
    return "CHƯA ĐẠT NGƯỠNG THAM CHIẾU — CẦN KỸ SƯ PCCC ĐỐI CHIẾU QUY CHUẨN";
  }
  return "DƯỚI NGƯỠNG DANH MỤC ĐÃ XÉT — CẦN XÁC NHẬN PHẠM VI";
}

export function VerdictIcon({ status, className }: { status: AppraisalStatus; className?: string }) {
  if (status === "required") return <XCircle className={className} />;
  if (status === "insufficient_data") return <AlertTriangle className={className} />;
  return <CheckCircle className={className} />;
}

const STATE_BADGE: Record<string, { text: string; cls: string }> = {
  met: { text: "ĐÃ ĐẠT NGƯỠNG", cls: "bg-red-100 text-red-800 border-red-300" },
  not_met: { text: "CHƯA ĐẠT NGƯỠNG", cls: "bg-emerald-100 text-emerald-800 border-emerald-300" },
  missing: { text: "CHƯA NHẬP SỐ LIỆU", cls: "bg-amber-100 text-amber-800 border-amber-300" },
};

interface Props {
  basis: AppraisalBasis | null | undefined;
  isSubjectToAppraisal: boolean;
  variant: "compact" | "full";
}

export function LegalBasisPanel({ basis, isSubjectToAppraisal, variant }: Props) {
  const full = variant === "full";
  const status = resolveStatus(basis, isSubjectToAppraisal);
  const style = VERDICT_STYLES[status];
  const idPrefix = full ? "full-verdict" : "verdict";

  return (
    <div
      id={`${idPrefix}-legislative-notices`}
      className={`bg-white dark:bg-slate-900 border-2 border-slate-350 dark:border-slate-800 ${full ? "rounded-2xl p-6 space-y-4 shadow-lg flex-1" : "rounded-xl p-5 space-y-3 shadow-md"}`}
    >
      <h4 className={`font-display font-black text-[#6B0D0D] dark:text-red-400 ${full ? "text-[20px]" : "text-[18px]"} flex items-center gap-2 uppercase tracking-tight`}>
        <div className="w-6 h-6 rounded-lg bg-gradient-to-b from-red-500 to-red-700 flex items-center justify-center text-white shrink-0">
          <Info className="w-3.5 h-3.5" />
        </div>
        Căn cứ pháp lý áp dụng cho công trình này
      </h4>

      {!basis ? (
        <p className="text-xs text-slate-800 dark:text-slate-200 font-semibold leading-relaxed" data-testid="basis-missing">
          Chưa có dữ liệu căn cứ pháp lý chi tiết cho hồ sơ này. Vui lòng bấm “Kiểm duyệt hồ sơ” để hệ thống tính lại.
        </p>
      ) : (
        <>
          <div className="text-xs" data-testid="basis-category">
            <span className="font-black text-slate-900 dark:text-slate-100">Nhóm công năng áp dụng: </span>
            <span className="font-black text-brand-orange">{basis.categoryLabel}</span>
            <span className="block text-slate-600 dark:text-slate-400 font-semibold mt-0.5">{basis.categoryEvidence}</span>
          </div>

          <p className={`${full ? "text-sm" : "text-xs"} text-slate-900 dark:text-slate-100 font-semibold leading-relaxed`} data-testid="basis-legal-text">
            {basis.legalText}
          </p>

          {basis.ruleMode === "always" ? (
            <div className="p-4 rounded-xl border-2 border-dashed border-orange-355 dark:border-orange-800 bg-orange-50/50 dark:bg-orange-950/20 space-y-1" data-testid="basis-scale-independent">
              <span className="text-xs font-black text-orange-950 dark:text-orange-300 uppercase">Không phụ thuộc quy mô</span>
              <p className="text-slate-900 dark:text-slate-100 font-black text-sm">Các ngưỡng số tầng / diện tích sàn không áp dụng cho nhóm này</p>
              <span className="text-xs text-orange-850 dark:text-orange-300 font-bold block">(Công trình của bạn: {basis.actualScale})</span>
            </div>
          ) : (
            <div className={`grid grid-cols-1 ${basis.thresholds.length > 1 ? "md:grid-cols-2" : ""} gap-4`} data-testid="basis-thresholds">
              {basis.thresholds.map((row) => {
                const badge = STATE_BADGE[row.state];
                return (
                  <div key={row.key} className="p-4 rounded-xl border-2 border-dashed border-orange-355 dark:border-orange-800 bg-orange-50/50 dark:bg-orange-950/20 space-y-1" data-testid={`threshold-${row.key}`} data-state={row.state}>
                    <span className="text-xs font-black text-orange-950 dark:text-orange-300 uppercase">Ngưỡng {row.label}:</span>
                    <p className="text-slate-900 dark:text-slate-100 font-black text-sm">Yêu cầu {row.limitText}</p>
                    <span className="text-xs text-orange-850 dark:text-orange-300 font-bold block">(Công trình của bạn: {row.actualText})</span>
                    <span className={`inline-block mt-1 px-2 py-0.5 rounded border text-[10px] font-black ${badge.cls}`}>{badge.text}</span>
                  </div>
                );
              })}
            </div>
          )}

          {basis.missingFields.length > 0 && (
            <p className="text-xs font-black text-amber-800 dark:text-amber-400" data-testid="basis-missing-fields">
              Còn thiếu thông số: {basis.missingFields.map((k) => FIELD_LABELS[k] ?? k).join(", ")}.
            </p>
          )}

          <p className={`${full ? "text-sm" : "text-xs"} text-slate-900 dark:text-slate-100 font-semibold leading-relaxed ${full ? "pt-2 border-t border-slate-200 dark:border-slate-800" : ""}`}>
            <span className={`${style.conclusion} font-black block`} data-testid="basis-conclusion">
              ➔ {basis.conclusion}
            </span>
          </p>
        </>
      )}
    </div>
  );
}
