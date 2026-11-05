import React, { useState, useMemo } from "react";
import { ChecklistItem } from "../../../types";
import { ChecklistFilterBar, QuickStatusFilter } from "./ChecklistFilterBar";
import { ChecklistResultBadge } from "./ChecklistResultBadge";

interface ComplianceChecklistViewProps {
  checklist: ChecklistItem[];
}

const isPassResult = (res: string) =>
  res === "Đạt" || res === "Không bắt buộc" || res === "Dưới ngưỡng danh mục";

const isFailResult = (res: string) => res === "Không đạt";

const isWarnResult = (res: string) => !isPassResult(res) && !isFailResult(res);

export const ComplianceChecklistView: React.FC<ComplianceChecklistViewProps> = ({ checklist }) => {
  const [search, setSearch] = useState("");
  const [quickFilter, setQuickFilter] = useState<QuickStatusFilter>("all");
  const [filterResult, setFilterResult] = useState<string>("all");

  const statusCounts = useMemo(() => {
    let pass = 0;
    let warn = 0;
    let fail = 0;
    for (const item of checklist) {
      const r = String(item.result);
      if (isPassResult(r)) pass++;
      else if (isFailResult(r)) fail++;
      else warn++;
    }
    return { all: checklist.length, pass, warn, fail };
  }, [checklist]);

  const filteredItems = useMemo(() => {
    return checklist.filter((item) => {
      const matchSearch =
        !search ||
        (item.criteria || "").toLowerCase().includes(search.toLowerCase()) ||
        (item.category || "").toLowerCase().includes(search.toLowerCase()) ||
        (item.requirement || "").toLowerCase().includes(search.toLowerCase()) ||
        (item.note && item.note.toLowerCase().includes(search.toLowerCase()));

      const res = String(item.result);
      const matchQuick =
        quickFilter === "all" ||
        (quickFilter === "pass" && isPassResult(res)) ||
        (quickFilter === "warn" && isWarnResult(res)) ||
        (quickFilter === "fail" && isFailResult(res));

      const matchSelect = filterResult === "all" || res === filterResult;
      return matchSearch && matchQuick && matchSelect;
    });
  }, [checklist, search, quickFilter, filterResult]);

  const handleSelectQuickFilter = (next: QuickStatusFilter) => {
    setQuickFilter(next);
    setFilterResult("all");
  };

  const handleSelectDropdownFilter = (val: string) => {
    setFilterResult(val);
    setQuickFilter("all");
  };

  return (
    <div className="flex-1 flex flex-col h-full bg-white dark:bg-slate-900 p-3 sm:p-4 space-y-3 overflow-hidden">
      <ChecklistFilterBar
        quickFilter={quickFilter}
        filterResult={filterResult}
        search={search}
        totalCount={checklist.length}
        statusCounts={statusCounts}
        onSelectQuickFilter={handleSelectQuickFilter}
        onSelectDropdownFilter={handleSelectDropdownFilter}
        onChangeSearch={setSearch}
      />

      <div className="flex-1 overflow-y-auto border border-slate-200 dark:border-slate-800 rounded-2xl custom-scrollbar">
        {filteredItems.length === 0 ? (
          <div className="p-10 text-center text-xs text-slate-500 dark:text-slate-400">
            Không có hạng mục nào khớp với bộ lọc hiện tại.
          </div>
        ) : (
          <>
            {/* Mobile Card List View (< sm) */}
            <div className="sm:hidden divide-y divide-slate-100 dark:divide-slate-800">
              {filteredItems.map((item) => (
                <div key={`m-item-${item.stt}`} className="p-3 space-y-2 hover:bg-slate-50/70 dark:hover:bg-slate-800/50">
                  <div className="flex items-start justify-between gap-2">
                    <span className="font-bold text-xs text-slate-800 dark:text-slate-200">#{item.stt} {item.category}</span>
                    <ChecklistResultBadge result={item.result} />
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
                  <tr key={`item-${item.stt}`} data-testid={`checklist-row-${item.stt}`} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/50 transition-colors">
                    <td className="px-3.5 py-2.5 text-center font-mono text-slate-500 dark:text-slate-400">{item.stt}</td>
                    <td className="px-3.5 py-2.5 font-bold text-slate-800 dark:text-slate-200">{item.category}</td>
                    <td className="px-3.5 py-2.5 space-y-1">
                      <p className="font-semibold text-slate-900 dark:text-slate-100">{item.criteria}</p>
                      <p className="text-slate-500 dark:text-slate-400 text-[11px] leading-relaxed">{item.requirement}</p>
                      {item.note && <p className="text-amber-800 dark:text-amber-300 font-medium text-[11px] bg-amber-50/60 dark:bg-amber-950/40 p-1 rounded border border-amber-100 dark:border-amber-900/60">{item.note}</p>}
                    </td>
                    <td className="px-3.5 py-2.5">
                      <ChecklistResultBadge result={item.result} />
                    </td>
                    <td className="px-3.5 py-2.5 text-[11px] font-mono text-slate-600 dark:text-slate-400">{item.reference || "QCVN 06:2022"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  );
};
