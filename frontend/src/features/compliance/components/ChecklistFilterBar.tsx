import React from "react";
import { Search, Filter, CheckCircle2, XCircle, AlertCircle } from "lucide-react";

export type QuickStatusFilter = "all" | "pass" | "warn" | "fail";

interface StatusCounts {
  all: number;
  pass: number;
  warn: number;
  fail: number;
}

interface ChecklistFilterBarProps {
  quickFilter: QuickStatusFilter;
  filterResult: string;
  search: string;
  totalCount: number;
  statusCounts: StatusCounts;
  onSelectQuickFilter: (filter: QuickStatusFilter) => void;
  onSelectDropdownFilter: (filter: string) => void;
  onChangeSearch: (val: string) => void;
}

export const ChecklistFilterBar: React.FC<ChecklistFilterBarProps> = ({
  quickFilter,
  filterResult,
  search,
  totalCount,
  statusCounts,
  onSelectQuickFilter,
  onSelectDropdownFilter,
  onChangeSearch,
}) => {
  return (
    <div className="space-y-2.5 shrink-0">
      {/* Quick filter pills */}
      <div
        role="tablist"
        aria-label="Bộ lọc trạng thái Checklist PCCC"
        data-testid="checklist-quick-filter-bar"
        className="flex flex-wrap items-center gap-1.5 bg-slate-50 dark:bg-slate-800/70 p-1.5 rounded-xl border border-slate-200/80 dark:border-slate-700/80"
      >
        <button
          type="button"
          data-testid="filter-all"
          onClick={() => onSelectQuickFilter("all")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            quickFilter === "all" && filterResult === "all"
              ? "bg-slate-900 dark:bg-slate-100 text-white dark:text-slate-900 shadow-xs"
              : "text-slate-600 dark:text-slate-300 hover:bg-white dark:hover:bg-slate-700"
          }`}
        >
          <span>Tất cả</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-white/20 dark:bg-slate-900/20">
            {statusCounts.all}
          </span>
        </button>

        <button
          type="button"
          data-testid="filter-pass"
          onClick={() => onSelectQuickFilter("pass")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            quickFilter === "pass"
              ? "bg-emerald-600 text-white shadow-xs"
              : "text-emerald-700 dark:text-emerald-300 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
          }`}
        >
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Đạt</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-emerald-100/80 dark:bg-emerald-900 text-emerald-900 dark:text-emerald-100">
            {statusCounts.pass}
          </span>
        </button>

        <button
          type="button"
          data-testid="filter-warn"
          onClick={() => onSelectQuickFilter("warn")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            quickFilter === "warn"
              ? "bg-amber-500 text-white shadow-xs"
              : "text-amber-700 dark:text-amber-300 hover:bg-amber-50 dark:hover:bg-amber-950/40"
          }`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          <span>Cảnh báo</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-amber-100/80 dark:bg-amber-900 text-amber-900 dark:text-amber-100">
            {statusCounts.warn}
          </span>
        </button>

        <button
          type="button"
          data-testid="filter-fail"
          onClick={() => onSelectQuickFilter("fail")}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
            quickFilter === "fail"
              ? "bg-red-600 text-white shadow-xs"
              : "text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-950/40"
          }`}
        >
          <XCircle className="w-3.5 h-3.5" />
          <span>Không đạt</span>
          <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-red-100/80 dark:bg-red-900 text-red-900 dark:text-red-100">
            {statusCounts.fail}
          </span>
        </button>
      </div>

      {/* Search and dropdown */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            data-testid="checklist-search"
            value={search}
            onChange={(e) => onChangeSearch(e.target.value)}
            placeholder="Tìm kiếm tiêu chí kỹ thuật, hạng mục PCCC..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl text-xs outline-none focus:bg-white dark:focus:bg-slate-800 focus:border-brand-orange"
          />
        </div>

        <div className="flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300 self-end sm:self-auto">
          <Filter className="w-3.5 h-3.5 text-slate-400" />
          <select
            data-testid="checklist-status-select"
            value={filterResult}
            onChange={(e) => onSelectDropdownFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 rounded-xl text-xs outline-none focus:bg-white dark:focus:bg-slate-800"
          >
            <option value="all">Chi tiết trạng thái ({totalCount})</option>
            <option value="Đạt">Đạt</option>
            <option value="Không đạt">Không đạt</option>
            <option value="Thuộc diện thẩm định">Thuộc diện thẩm định</option>
            <option value="Dưới ngưỡng danh mục">Dưới ngưỡng danh mục</option>
            <option value="Khuyến nghị mạnh">Khuyến nghị mạnh</option>
            <option value="Khuyến nghị">Khuyến nghị</option>
            <option value="Cần đo đạc">Cần đo đạc</option>
            <option value="Cần xem xét">Cần xem xét</option>
            <option value="Không bắt buộc">Không bắt buộc</option>
          </select>
        </div>
      </div>
    </div>
  );
};

