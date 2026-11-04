import React from "react";
import { PanelLeft, Sparkles, ScanLine, Loader2, MessageSquare, ClipboardCheck, Scale, Sun, Moon } from "lucide-react";
import { ActiveTab, ProjectInfo } from "../types";
import { AuthUser } from "../lib/api";
import { SpecsSummaryBar } from "../features/project-specs/components/SpecsSummaryBar";
import { ExportReportsDropdown } from "../features/compliance/components/ExportReportsDropdown";
import { AiHealthIndicator } from "../components/AiHealthIndicator";

interface AppHeaderProps {
  onToggleSidebar: () => void;
  project: ProjectInfo;
  reviewState: "draft" | "reviewed";
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
  onOpenSpecsDrawer: () => void;
  onOpenOcrUpload: () => void;
  onTriggerAppraisal: () => void;
  isPending: boolean;
  hasAreaContradiction?: boolean;
  hasChecklist?: boolean;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onExportDocx: () => void;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingDocx: boolean;
  isExportingPdf: boolean;
  isExportingJson: boolean;
  currentUser?: AuthUser | null;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  onToggleSidebar,
  project,
  reviewState,
  activeTab,
  onChangeTab,
  onOpenSpecsDrawer,
  onOpenOcrUpload,
  onTriggerAppraisal,
  isPending,
  hasAreaContradiction = false,
  hasChecklist = false,
  theme,
  onToggleTheme,
  onExportDocx,
  onExportPdf,
  onExportJson,
  isExportingDocx,
  isExportingPdf,
  isExportingJson,
  currentUser = null,
}) => {
  return (
    <header className="h-14 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-2.5 sm:px-3 flex items-center justify-between gap-1.5 shrink-0 z-30 transition-colors">
      <div className="flex items-center gap-1.5 min-w-0 shrink-0">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-1.5 text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-white rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer shrink-0"
          title="Đóng/mở danh sách hồ sơ"
        >
          <PanelLeft className="w-5 h-5" />
        </button>

        <SpecsSummaryBar
          project={project}
          reviewState={reviewState}
          onOpenDrawer={onOpenSpecsDrawer}
        />
      </div>

      <div className="hidden md:flex items-center p-1 bg-slate-100 dark:bg-slate-800/90 border border-transparent dark:border-slate-700/60 rounded-xl shrink-0">
        <button
          type="button"
          onClick={() => onChangeTab("chat")}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs font-bold rounded-lg whitespace-nowrap transition-all cursor-pointer ${
            activeTab === "chat" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white"
          }`}
        >
          <MessageSquare className="w-3.5 h-3.5 text-brand-orange shrink-0" />
          <span>Tư vấn AI</span>
        </button>

        <button
          type="button"
          onClick={() => onChangeTab("checklist")}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs font-bold rounded-lg whitespace-nowrap transition-all cursor-pointer ${
            activeTab === "checklist" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white"
          }`}
        >
          <ClipboardCheck className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400 shrink-0" />
          <span>Bảng tiêu chí</span>
        </button>

        <button
          type="button"
          onClick={() => onChangeTab("verdict")}
          className={`flex items-center gap-1.5 px-2 py-1 text-xs font-bold rounded-lg whitespace-nowrap transition-all cursor-pointer ${
            activeTab === "verdict" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 dark:text-slate-300 hover:text-slate-800 dark:hover:text-white"
          }`}
        >
          <Scale className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>Căn cứ pháp lý</span>
        </button>
      </div>

      <div className="flex items-center gap-1.5 shrink-0">
        <AiHealthIndicator currentUser={currentUser} />

        <button
          type="button"
          onClick={onToggleTheme}
          className="p-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors cursor-pointer shadow-xs shrink-0"
          title={theme === "dark" ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối"}
        >
          {theme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
        </button>

        <button
          type="button"
          onClick={onOpenOcrUpload}
          disabled={isPending}
          className="hidden sm:inline-flex items-center gap-1 px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold whitespace-nowrap shrink-0 shadow-xs transition-all cursor-pointer disabled:opacity-50"
          title="Tải bản vẽ PDF / Ảnh để AI bóc tách (OCR)"
        >
          <ScanLine className="w-3.5 h-3.5 text-brand-orange shrink-0" />
          <span className="hidden 2xl:inline">Đọc bản vẽ (OCR)</span>
          <span className="2xl:hidden">OCR</span>
        </button>

        <button
          type="button"
          disabled={isPending || hasAreaContradiction}
          onClick={onTriggerAppraisal}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:opacity-50 text-white text-xs font-bold whitespace-nowrap shrink-0 shadow-xs transition-all cursor-pointer"
          title={hasAreaContradiction ? "Vui lòng sửa mâu thuẫn diện tích trước khi kiểm duyệt" : "Rà soát toàn bộ quy chuẩn và tính toán kết luận PCCC"}
        >
          {isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" /> : <Sparkles className="w-3.5 h-3.5 shrink-0" />}
          <span className="hidden 2xl:inline">Kiểm duyệt hồ sơ</span>
          <span className="2xl:hidden">Kiểm duyệt</span>
        </button>

        <ExportReportsDropdown
          onExportDocx={onExportDocx}
          onExportPdf={onExportPdf}
          onExportJson={onExportJson}
          isExportingDocx={isExportingDocx}
          isExportingPdf={isExportingPdf}
          isExportingJson={isExportingJson}
          disabled={isPending || hasAreaContradiction || !hasChecklist || reviewState === "draft"}
        />
      </div>
    </header>
  );
};
