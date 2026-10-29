import React from "react";
import { Ruler } from "lucide-react";
import { ProjectInfo } from "../../../types";

interface SpecsScaleFieldsProps {
  localFloors: string | number;
  setLocalFloors: (val: string | number) => void;
  localBasements: string | number;
  setLocalBasements: (val: string | number) => void;
  localPcccHeight: string | number;
  setLocalPcccHeight: (val: string | number) => void;
  localFloorArea: string | number;
  setLocalFloorArea: (val: string | number) => void;
  localTotalFloorArea: string | number;
  setLocalTotalFloorArea: (val: string | number) => void;
  localFireRating: string;
  setLocalFireRating: (val: string) => void;
  localCommDetails: string;
  setLocalCommDetails: (val: string) => void;
  onCommitField: (field: keyof ProjectInfo, val: unknown) => void;
}

const FIRE_RATINGS = ["Bậc I", "Bậc II", "Bậc III", "Bậc IV", "Bậc V"];

interface ScaleInputProps {
  id: string;
  label: string;
  value: string | number;
  placeholder: string;
  max: number;
  step?: string;
  onChange: (val: string | number) => void;
  onBlur: () => void;
}

const ScaleInput: React.FC<ScaleInputProps> = ({ id, label, value, placeholder, max, step, onChange, onBlur }) => (
  <div>
    <label className="block text-[11px] font-bold text-slate-600 mb-1">{label}</label>
    <input
      id={id}
      type="number"
      min="0"
      max={max}
      step={step}
      value={value}
      onFocus={(e) => e.target.select()}
      onChange={(e) => onChange(e.target.value === "" ? "" : Math.min(max, Math.max(0, Number(e.target.value))))}
      onBlur={onBlur}
      placeholder={placeholder}
      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-brand-orange outline-none font-medium text-slate-900"
    />
  </div>
);

export const SpecsScaleFields: React.FC<SpecsScaleFieldsProps> = ({
  localFloors, setLocalFloors, localBasements, setLocalBasements,
  localPcccHeight, setLocalPcccHeight, localFloorArea, setLocalFloorArea,
  localTotalFloorArea, setLocalTotalFloorArea, localFireRating, setLocalFireRating,
  localCommDetails, setLocalCommDetails, onCommitField,
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700">
        <Ruler className="w-4 h-4 text-brand-orange" />
        <span>Quy mô kiến trúc &amp; PCCC</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <ScaleInput id="spec-floors" label="Số tầng nổi" value={localFloors} placeholder="4" max={200} onChange={setLocalFloors} onBlur={() => onCommitField("floors", Number(localFloors) || 0)} />
        <ScaleInput id="spec-basements" label="Số tầng hầm" value={localBasements} placeholder="0" max={20} onChange={setLocalBasements} onBlur={() => onCommitField("basements", Number(localBasements) || 0)} />
        <ScaleInput id="spec-pccc-height" label="Chiều cao PCCC (m)" value={localPcccHeight} placeholder="12" max={1000} step="0.1" onChange={setLocalPcccHeight} onBlur={() => onCommitField("pcccHeight", Number(localPcccHeight) || 0)} />

        <div>
          <label className="block text-[11px] font-bold text-slate-600 mb-1">Bậc chịu lửa</label>
          <select
            id="spec-fire-rating"
            value={localFireRating}
            onChange={(e) => { setLocalFireRating(e.target.value); onCommitField("fireRating", e.target.value); }}
            className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-brand-orange outline-none font-medium text-slate-900"
          >
            <option value="">Chưa lựa chọn</option>
            {FIRE_RATINGS.map((r) => (<option key={r} value={r}>{r}</option>))}
          </select>
        </div>

        <ScaleInput id="spec-floor-area" label="Diện tích sàn (m²)" value={localFloorArea} placeholder="100" max={1000000} onChange={setLocalFloorArea} onBlur={() => onCommitField("floorArea", Number(localFloorArea) || 0)} />
        <ScaleInput id="spec-total-floor-area" label="Tổng DT sàn (m²)" value={localTotalFloorArea} placeholder="400" max={10000000} onChange={setLocalTotalFloorArea} onBlur={() => onCommitField("totalFloorArea", Number(localTotalFloorArea) || 0)} />
      </div>

      <div>
        <label className="block text-[11px] font-bold text-slate-600 mb-1">Chi tiết kinh doanh / công năng bổ trợ</label>
        <input
          id="spec-comm-details"
          type="text"
          value={localCommDetails}
          onFocus={(e) => e.target.select()}
          onChange={(e) => setLocalCommDetails(e.target.value)}
          onBlur={() => onCommitField("commercialDetails", localCommDetails)}
          placeholder="Ví dụ: Tầng 1 văn phòng, tầng 2-4 căn hộ"
          className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-brand-orange outline-none font-medium text-slate-900 text-xs"
        />
      </div>
    </div>
  );
};
