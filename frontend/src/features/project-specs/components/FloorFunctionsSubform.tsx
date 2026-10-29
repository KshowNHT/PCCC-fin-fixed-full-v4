import React from "react";
import { Layers } from "lucide-react";

interface FloorFunctionsSubformProps {
  floorsCount: number;
  floorFunctions: string[];
  onChangeFloorFunction: (index: number, value: string) => void;
}

const FLOOR_FUNCTION_OPTIONS = [
  { value: "", label: "Chưa nhập công năng tầng" },
  { value: "Nhà ở riêng lẻ / Dân dụng", label: "Nhà ở dân dụng" },
  { value: "Kinh doanh thương mại / Dịch vụ nhẹ", label: "Cửa hàng / Kinh doanh" },
  { value: "Dịch vụ giải trí Karaoke, Vũ trường", label: "Cơ sở Karaoke / Bar" },
  { value: "Văn phòng, Phòng làm việc", label: "Văn phòng làm việc" },
  { value: "Nhà kho lưu trữ hàng hóa", label: "Kho chứa đồ / Kệ chứa" },
  { value: "Bãi đỗ xe hoặc gian kĩ thuật", label: "Gara / Kỹ thuật" },
  { value: "Xưởng sản xuất / Dây chuyền công nghệ", label: "Xưởng sản xuất" },
  { value: "Lớp học / Phòng thí nghiệm", label: "Lớp học / Giáo dục" },
  { value: "Khán phòng / Rạp hát / Khu vực khán giả", label: "Hội trường / Rạp hát" },
  { value: "Khu vực bếp ăn / Căng tin tập thể", label: "Bếp ăn / Căng tin" },
];

export const FloorFunctionsSubform: React.FC<FloorFunctionsSubformProps> = ({
  floorsCount,
  floorFunctions,
  onChangeFloorFunction,
}) => {
  if (floorsCount <= 1) return null;

  return (
    <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-2">
      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
        <Layers className="w-3.5 h-3.5 text-brand-orange" />
        <span>Công năng chi tiết {floorsCount} tầng nổi</span>
      </div>

      <div className="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar pr-1">
        {Array.from({ length: floorsCount }).map((_, idx) => {
          const floorNum = idx + 1;
          const currentVal = floorFunctions[idx] || "";
          return (
            <div key={`floor-${floorNum}`} className="flex items-center gap-2 text-xs">
              <span className="w-14 shrink-0 font-medium text-slate-600">Tầng {floorNum}:</span>
              <select
                value={currentVal}
                onChange={(e) => onChangeFloorFunction(idx, e.target.value)}
                className="flex-1 px-2.5 py-1.5 bg-white border border-slate-200 rounded-lg text-xs outline-none focus:border-brand-orange text-slate-800"
              >
                {FLOOR_FUNCTION_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      </div>
    </div>
  );
};

