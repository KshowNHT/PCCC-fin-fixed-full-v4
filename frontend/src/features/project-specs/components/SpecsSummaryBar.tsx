import React from "react";
import { SlidersHorizontal, CheckCircle2, AlertCircle } from "lucide-react";
import { ProjectInfo } from "../../../types";

interface SpecsSummaryBarProps {
  project: ProjectInfo;
  reviewState: "draft" | "reviewed";
  onOpenDrawer: () => void;
  disabled?: boolean;
}

export const SpecsSummaryBar: React.FC<SpecsSummaryBarProps> = ({
  project,
  reviewState,
  onOpenDrawer,
  disabled = false,
}) => {
  const isReviewed = reviewState === "reviewed";
  const typeText = project.type || "Chưa chọn công năng";
  const floorsText = project.floors ? `${project.floors} tầng` : null;
  const areaText = project.totalFloorArea ? `${project.totalFloorArea}m²` : null;
  const heightText = project.pcccHeight ? `Cao ${project.pcccHeight}m` : null;

  const summaryParts = [typeText, floorsText, areaText, heightText].filter(Boolean);

  return (
    <div className="flex items-center gap-1.5 sm:gap-2 min-w-0">
      <button
        type="button"
        disabled={disabled}
        onClick={onOpenDrawer}
        className="inline-flex items-center gap-1.5 sm:gap-2 px-2.5 sm:px-3 py-1.5 rounded-xl bg-slate-100 hover:bg-slate-200/70 text-slate-700 text-xs font-semibold transition-all cursor-pointer border border-slate-200/80 shadow-xs min-w-0"
        title="Bấm để mở bảng điều chỉnh thông số công trình"
      >
        <SlidersHorizontal className="w-3.5 h-3.5 text-slate-500 shrink-0" />
        <span className="truncate max-w-[100px] xs:max-w-[140px] sm:max-w-[240px] md:max-w-[360px]">
          {summaryParts.join(" • ")}
        </span>
      </button>

      <span
        className={`inline-flex items-center gap-1 px-2 sm:px-2.5 py-1 rounded-full text-[11px] font-bold shrink-0 ${
          isReviewed
            ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
            : "bg-amber-50 text-amber-700 border border-amber-200"
        }`}
        title={isReviewed ? "Hồ sơ đã được kiểm duyệt" : "Thông số đang là bản nháp"}
      >
        {isReviewed ? (
          <>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
            <span className="hidden sm:inline">Đã kiểm duyệt</span>
          </>
        ) : (
          <>
            <AlertCircle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="hidden sm:inline">Bản nháp</span>
          </>
        )}
      </span>
    </div>
  );
};
