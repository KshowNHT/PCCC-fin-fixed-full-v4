import React, { useState, useMemo } from "react";
import { Search, Filter, CheckCircle2, XCircle, AlertCircle, HelpCircle } from "lucide-react";
import { ChecklistItem } from "../../../types";

interface ComplianceChecklistViewProps {
  checklist: ChecklistItem[];
}

export const ComplianceChecklistView: React.FC<ComplianceChecklistViewProps> = ({ checklist }) => {
  const [search, setSearch] = useState("");
  const [filterResult, setFilterResult] = useState<string>("all");

  const filteredItems = useMemo(() => {
    return checklist.filter((item) => {
      const matchSearch =
        !search ||
        item.criteria.toLowerCase().includes(search.toLowerCase()) ||
        item.category.toLowerCase().includes(search.toLowerCase()) ||
        item.requirement.toLowerCase().includes(search.toLowerCase());
      const matchFilter = filterResult === "all" || item.result === filterResult;
      return matchSearch && matchFilter;
    });
  }, [checklist, search, filterResult]);

  const getResultBadge = (res: ChecklistItem["result"]) => {
    switch (res) {
      case "Đạt":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200"><CheckCircle2 className="w-3 h-3 text-emerald-600" />Đạt</span>;
      case "Không đạt":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-50 text-red-700 border border-red-200"><XCircle className="w-3 h-3 text-red-600" />Không đạt</span>;
      case "Không bắt buộc":
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200"><HelpCircle className="w-3 h-3 text-slate-400" />Không bắt buộc</span>;
      default:
        return <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200"><AlertCircle className="w-3 h-3 text-amber-600" />{res}</span>;
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-white dark:bg-slate-900 p-3 sm:p-4 space-y-3 overflow-hidden">
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Tìm kiếm tiêu chí kỹ thuật, hạng mục PCCC..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl text-xs outline-none focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 self-end sm:self-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            value={filterResult}
            onChange={(e) => setFilterResult(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-xl text-xs outline-none focus:bg-white dark:focus:bg-slate-800"
          >
            <option value="all">Tất cả ({checklist.length})</option>
            <option value="Đạt">Đạt</option>
            <option value="Không đạt">Không đạt</option>
            <option value="Khuyến nghị mạnh">Khuyến nghị mạnh</option>
            <option value="Khuyến nghị">Khuyến nghị</option>
            <option value="Cần xem xét">Cần xem xét</option>
            <option value="Không bắt buộc">Không bắt buộc</option>
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto border border-slate-200 dark:border-slate-800 rounded-2xl custom-scrollbar">
        {/* Mobile Card List View (< sm) */}
        <div className="sm:hidden divide-y divide-slate-100 dark:divide-slate-800">
          {filteredItems.map((item) => (
            <div key={`m-item-${item.stt}`} className="p-3 space-y-2 hover:bg-slate-50/70 dark:hover:bg-slate-800/50">
              <div className="flex items-start justify-between gap-2">
                <span className="font-bold text-xs text-slate-800 dark:text-slate-200">#{item.stt} {item.category}</span>
                {getResultBadge(item.result)}
              </div>
              <p className="text-xs font-semibold text-slate-900 dark:text-slate-100">{item.criteria}</p>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">{item.requirement}</p>
              {item.note && <p className="text-amber-800 dark:text-amber-300 text-[11px] bg-amber-50 dark:bg-amber-950/40 p-1.5 rounded border border-amber-200 dark:border-amber-900/60">{item.note}</p>}
              <p className="text-[10px] font-mono text-slate-400 dark:text-slate-500">Căn cứ: {item.reference || "QCVN 06:2022"}</p>
            </div>
          ))}
        </div>

        {/* Desktop / Tablet Table View (>= sm) */}
        <table className="hidden sm:table w-full text-left text-xs divide-y divide-slate-200 dark:divide-slate-800">
          <thead className="bg-slate-50 dark:bg-slate-800/90 text-slate-700 dark:text-slate-300 uppercase font-bold text-[10.5px] sticky top-0 z-10">
            <tr>
              <th className="px-3.5 py-2.5 w-12 text-center">STT</th>
              <th className="px-3.5 py-2.5 w-44">Hạng mục</th>
              <th className="px-3.5 py-2.5 min-w-[200px]">Tiêu chí &amp; Yêu cầu quy chuẩn</th>
              <th className="px-3.5 py-2.5 w-36">Kết quả</th>
              <th className="px-3.5 py-2.5 min-w-[160px]">Căn cứ quy chuẩn</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800 bg-white dark:bg-slate-900">
            {filteredItems.map((item) => (
              <tr key={`item-${item.stt}`} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                <td className="px-3.5 py-2.5 text-center font-mono text-slate-500 dark:text-slate-400">{item.stt}</td>
                <td className="px-3.5 py-2.5 font-bold text-slate-800 dark:text-slate-200">{item.category}</td>
                <td className="px-3.5 py-2.5 space-y-1">
                  <p className="font-semibold text-slate-900 dark:text-slate-100">{item.criteria}</p>
                  <p className="text-slate-500 dark:text-slate-400 text-[11px] leading-relaxed">{item.requirement}</p>
                  {item.note && <p className="text-amber-800 dark:text-amber-300 font-medium text-[11px] bg-amber-50/60 dark:bg-amber-950/40 p-1 rounded border border-amber-100 dark:border-amber-900/60">{item.note}</p>}
                </td>
                <td className="px-3.5 py-2.5">{getResultBadge(item.result)}</td>
                <td className="px-3.5 py-2.5 text-[11px] font-mono text-slate-600 dark:text-slate-400">{item.reference || "QCVN 06:2022"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
