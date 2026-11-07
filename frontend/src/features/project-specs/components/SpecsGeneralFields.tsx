import React from "react";
import { Compass } from "lucide-react";
import { ProjectInfo } from "../../../types";

interface SpecsGeneralFieldsProps {
  localName: string;
  setLocalName: (val: string) => void;
  localInvestor: string;
  setLocalInvestor: (val: string) => void;
  localLocation: string;
  setLocalLocation: (val: string) => void;
  localType: string;
  setLocalType: (val: string) => void;
  onCommitField: (field: keyof ProjectInfo, val: unknown) => void;
}

const COMMON_BUILDING_TYPES = [
  "Cơ sở kinh doanh Karaoke, Vũ trường",
  "Quán Karaoke",
  "Nhà hỗn hợp",
  "Nhà ở riêng lẻ kết hợp kinh doanh",
  "Nhà ở riêng lẻ",
  "Nhà chung cư",
  "Văn phòng, khách sạn công cộng",
  "Khách sạn",
  "Văn phòng",
  "Chợ, Trung tâm thương mại",
  "Trung tâm thương mại",
  "Siêu thị",
  "Nhà để xe ô tô dạng kín",
  "Gara ô tô kín",
  "Nhà kho xếp giá đỡ kệ cao",
  "Nhà kho",
  "Nhà máy, nhà xưởng sản xuất",
  "Nhà máy / nhà xưởng",
  "Cơ sở giáo dục, trường học",
  "Bệnh viện, cơ sở y tế",
  "Rạp hát, hội trường, trung tâm tổ chức sự kiện",
  "Cửa hàng xăng dầu",
];

export const SpecsGeneralFields: React.FC<SpecsGeneralFieldsProps> = ({
  localName,
  setLocalName,
  localInvestor,
  setLocalInvestor,
  localLocation,
  setLocalLocation,
  localType,
  setLocalType,
  onCommitField,
}) => {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
        <Compass className="w-4 h-4 text-brand-orange" />
        <span>Thông tin chung công trình</span>
      </div>

      <div className="space-y-2 text-xs">
        <div>
          <label className="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Tên công trình</label>
          <input
            id="spec-name"
            type="text"
            value={localName}
            onFocus={(e) => e.target.select()}
            onChange={(e) => setLocalName(e.target.value)}
            onBlur={() => onCommitField("name", localName)}
            placeholder="Ví dụ: Tòa nhà Karaoke Luxury 5 Tầng"
            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange outline-none font-medium text-slate-900 dark:text-slate-100 transition-colors"
          />
        </div>

        <div>
          <label className="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Loại công trình (Công năng chính)</label>
          <div className="relative">
            <input
              id="spec-type"
              type="text"
              list="building-type-suggestions"
              value={localType}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setLocalType(e.target.value)}
              onBlur={() => onCommitField("type", localType)}
              placeholder="Chọn hoặc nhập loại hình công trình..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange outline-none font-medium text-slate-900 dark:text-slate-100 transition-colors"
            />
            <datalist id="building-type-suggestions">
              {COMMON_BUILDING_TYPES.map((t) => (
                <option key={t} value={t} />
              ))}
            </datalist>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Chủ đầu tư</label>
            <input
              id="spec-investor"
              type="text"
              value={localInvestor}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setLocalInvestor(e.target.value)}
              onBlur={() => onCommitField("investor", localInvestor)}
              placeholder="Ông Nguyễn Văn A"
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange outline-none font-medium text-slate-900 dark:text-slate-100 transition-colors"
            />
          </div>

          <div>
            <label className="block text-[11px] font-bold text-slate-600 dark:text-slate-400 mb-1">Địa điểm</label>
            <input
              id="spec-location"
              type="text"
              value={localLocation}
              onFocus={(e) => e.target.select()}
              onChange={(e) => setLocalLocation(e.target.value)}
              onBlur={() => onCommitField("location", localLocation)}
              placeholder="Hà Nội, TP.HCM..."
              className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange outline-none font-medium text-slate-900 dark:text-slate-100 transition-colors"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
