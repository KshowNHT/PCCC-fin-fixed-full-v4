import React from "react";
import { ArrowDownToLine } from "lucide-react";

interface BasementFunctionsSubformProps {
  basementsCount: number;
  functions: string[];
  heights: number[];
  areas: number[];
  footprints: number[];
  onChangeField: (
    index: number,
    field: "functions" | "heights" | "areas" | "footprints",
    value: string | number
  ) => void;
}

const BASEMENT_OPTIONS = [
  { value: "", label: "Chưa nhập công năng" },
  { value: "Bãi đỗ xe hầm", label: "Bãi đỗ xe dưới hầm" },
  { value: "Gian kĩ thuật hầm", label: "Gian kỹ thuật / Trạm máy" },
  { value: "Thương mại hầm", label: "Kinh doanh / Thương mại" },
  { value: "Kho dưới hầm", label: "Kho chứa hàng hóa" },
  { value: "Khu vực sản xuất dưới hầm", label: "Khu vực sản xuất" },
  { value: "Công năng hỗn hợp khác hầm", label: "Hỗn hợp khác" },
];

export const BasementFunctionsSubform: React.FC<BasementFunctionsSubformProps> = ({
  basementsCount,
  functions,
  heights,
  areas,
  footprints,
  onChangeField,
}) => {
  if (basementsCount < 1) return null;

  return (
    <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3 space-y-2.5">
      <div className="flex items-center gap-1.5 text-xs font-bold text-slate-700">
        <ArrowDownToLine className="w-3.5 h-3.5 text-brand-orange" />
        <span>Thông số chi tiết {basementsCount} tầng hầm</span>
      </div>

      <div className="space-y-2.5 max-h-56 overflow-y-auto custom-scrollbar pr-1">
        {Array.from({ length: basementsCount }).map((_, idx) => {
          const bNum = idx + 1;
          const curFn = functions[idx] || "";
          const curHeight = heights[idx] ?? 0;
          const curArea = areas[idx] ?? 0;
          const curFootprint = footprints[idx] ?? 0;

          return (
            <div key={`basement-${bNum}`} className="bg-white p-2.5 rounded-lg border border-slate-200 text-xs space-y-2">
              <div className="font-bold text-slate-800 text-[11px] pb-1 border-b border-slate-100 flex justify-between">
                <span>Tầng hầm B{bNum}</span>
              </div>

              <div>
                <label className="block text-[10px] font-medium text-slate-500 mb-0.5">Công năng</label>
                <select
                  value={curFn}
                  onChange={(e) => onChangeField(idx, "functions", e.target.value)}
                  className="w-full px-2 py-1 bg-slate-50 border border-slate-200 rounded text-xs outline-none focus:bg-white focus:border-brand-orange text-slate-800"
                >
                  {BASEMENT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-3 gap-1.5">
                <div>
                  <span className="block text-[10px] font-medium text-slate-500">Cao (m)</span>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="0.1"
                    value={curHeight}
                    onFocus={(e) => e.target.select()}
                    onChange={(e) => onChangeField(idx, "heights", Math.min(100, Math.max(0, Number(e.target.value) || 0)))}
                    className="w-full px-1.5 py-1 bg-slate-50 border border-slate-200 rounded text-center text-xs outline-none focus:bg-white"
                  />
                </div>

                <div>
                  <span className="block text-[10px] font-medium text-slate-500">DT sàn (m²)</span>
                  <input
                    type="number"
                    min="0"
                    max="1000000"
                    value={curArea}
                    onFocus={(e) => e.target.select()}
                    onChange={(e) => onChangeField(idx, "areas", Math.min(1000000, Math.max(0, Number(e.target.value) || 0)))}
                    className="w-full px-1.5 py-1 bg-slate-50 border border-slate-200 rounded text-center text-xs outline-none focus:bg-white"
                  />
                </div>

                <div>
                  <span className="block text-[10px] font-medium text-slate-500">DT xây dựng</span>
                  <input
                    type="number"
                    min="0"
                    max="1000000"
                    value={curFootprint}
                    onFocus={(e) => e.target.select()}
                    onChange={(e) => onChangeField(idx, "footprints", Math.min(1000000, Math.max(0, Number(e.target.value) || 0)))}
                    className="w-full px-1.5 py-1 bg-slate-50 border border-slate-200 rounded text-center text-xs outline-none focus:bg-white"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

