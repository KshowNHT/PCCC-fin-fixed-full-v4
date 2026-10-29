import React from "react";
import { CheckCircle2, Building2 } from "lucide-react";
import { ProjectInfo, BuildingComponent } from "../../../types";

interface ExtractionPreviewProps {
  extracted: Partial<ProjectInfo>;
  coverageNotice?: string;
}

const FIELD_LABELS: Record<string, string> = {
  name: "Tên công trình",
  location: "Địa điểm",
  investor: "Chủ đầu tư",
  designer: "Đơn vị thiết kế",
  type: "Loại công trình",
  length: "Chiều dài (m)",
  width: "Chiều rộng (m)",
  height: "Chiều cao (m)",
  pcccHeight: "Chiều cao PCCC (m)",
  floorArea: "Diện tích sàn (m²)",
  totalFloorArea: "Tổng diện tích sàn (m²)",
  floors: "Số tầng nổi",
  basements: "Số tầng hầm",
  fireRating: "Bậc chịu lửa",
  commercialDetails: "Chi tiết kinh doanh",
};

export const ExtractionPreview: React.FC<ExtractionPreviewProps> = ({
  extracted,
  coverageNotice,
}) => {
  const components: BuildingComponent[] = extracted.components || [];
  const fields = Object.entries(extracted).filter(([key]) => key !== "components");

  return (
    <div className="space-y-3.5">
      <div className="flex items-center gap-2 p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-xl text-xs font-medium">
        <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
        <span>
          Đã trích xuất thành công {fields.length} thông số. Vui lòng đối soát trước khi áp dụng.
        </span>
      </div>

      {coverageNotice && (
        <p className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200">
          {coverageNotice}
        </p>
      )}

      <div className="border border-slate-200 rounded-xl overflow-hidden max-h-56 overflow-y-auto custom-scrollbar divide-y divide-slate-100 bg-white">
        {fields.map(([key, val]) => (
          <div key={key} className="flex justify-between items-center px-3.5 py-2 text-xs">
            <span className="text-slate-500">{FIELD_LABELS[key] || key}</span>
            <span className="font-semibold text-slate-800 text-right ml-4">
              {Array.isArray(val) ? val.join(", ") : String(val ?? "")}
            </span>
          </div>
        ))}
      </div>

      {components.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
            <Building2 className="w-4 h-4 text-brand-orange" />
            Hạng mục công trình độc lập ({components.length} nhà):
          </p>
          <div className="space-y-2 max-h-44 overflow-y-auto custom-scrollbar">
            {components.map((item) => (
              <div key={item.id} className="p-2.5 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                <p className="font-bold text-slate-800">
                  {item.name} — {item.type || "Chưa rõ công năng"}
                </p>
                <p className="text-slate-600 text-[11px]">
                  {item.floors || "?"} tầng; cao {item.height || "?"}m; tổng sàn {item.totalFloorArea || "?"}m²; {item.fireRating || "Chưa rõ bậc"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

