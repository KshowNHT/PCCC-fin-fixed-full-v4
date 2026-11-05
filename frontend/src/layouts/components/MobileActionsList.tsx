import React from "react";
import { Sparkles, ScanLine, Loader2, MessageSquare, ClipboardCheck, Scale, Sun, Moon } from "lucide-react";
import { ActiveTab } from "../../types";
import { MobileExportButtons } from "./MobileExportButtons";

export interface MobileActionsListProps {
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
  onOpenOcrUpload: () => void;
  onTriggerAppraisal: () => void;
  isPending: boolean;
  hasAreaContradiction: boolean;
  hasChecklist: boolean;
  reviewState: "draft" | "reviewed";
  onExportDocx: () => void;
  onExportPdf: () => void;
  onExportJson: () => void;
  isExportingDocx: boolean;
  isExportingPdf: boolean;
  isExportingJson: boolean;
  theme: "light" | "dark";
  onToggleTheme: () => void;
  onClose: () => void;
}

export const MobileActionsList: React.FC<MobileActionsListProps> = ({
  activeTab,
  onChangeTab,
  onOpenOcrUpload,
  onTriggerAppraisal,
  isPending,
  hasAreaContradiction,
  hasChecklist,
  reviewState,
  onExportDocx,
  onExportPdf,
  onExportJson,
  isExportingDocx,
  isExportingPdf,
  isExportingJson,
  theme,
  onToggleTheme,
  onClose,
}) => {
  const isExportDisabled = isPending || hasAreaContradiction || !hasChecklist || reviewState === "draft";

  const handleSelectTab = (tab: ActiveTab) => {
    onChangeTab(tab);
    onClose();
  };

  return (
    <div className="flex flex-col gap-3 text-xs">
      <div className="flex flex-col gap-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Hành động chính
        </span>
        <button
          type="button"
          disabled={isPending || hasAreaContradiction}
          onClick={() => { onTriggerAppraisal(); onClose(); }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:opacity-50 text-white font-bold shadow-xs transition-all cursor-pointer"
        >
          {isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          <span>Kiểm duyệt hồ sơ</span>
        </button>

        <button
          type="button"
          disabled={isPending}
          onClick={() => { onOpenOcrUpload(); onClose(); }}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-100 font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
        >
          <ScanLine className="w-4 h-4 text-brand-orange" />
          <span>Đọc bản vẽ kiến trúc (OCR)</span>
        </button>
      </div>

      <div className="flex flex-col gap-2 pt-1 border-t border-slate-100 dark:border-slate-800">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Xuất báo cáo thẩm duyệt
        </span>
        <MobileExportButtons
          onExportDocx={onExportDocx}
          onExportPdf={onExportPdf}
          onExportJson={onExportJson}
          isExportingDocx={isExportingDocx}
          isExportingPdf={isExportingPdf}
          isExportingJson={isExportingJson}
          disabled={isExportDisabled}
          onClose={onClose}
        />
      </div>

      <div className="flex flex-col gap-2 pt-1 border-t border-slate-100 dark:border-slate-800">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
          Chuyển màn hình
        </span>
        <div className="grid grid-cols-3 gap-1.5 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
          <button
            type="button"
            onClick={() => handleSelectTab("chat")}
            className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg font-bold transition-all cursor-pointer ${
              activeTab === "chat" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 hover:text-slate-800 dark:text-slate-300"
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5 text-brand-orange" />
            <span>Tư vấn</span>
          </button>
          <button
            type="button"
            onClick={() => handleSelectTab("checklist")}
            className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg font-bold transition-all cursor-pointer ${
              activeTab === "checklist" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 hover:text-slate-800 dark:text-slate-300"
            }`}
          >
            <ClipboardCheck className="w-3.5 h-3.5 text-blue-600" />
            <span>Tiêu chí</span>
          </button>
          <button
            type="button"
            onClick={() => handleSelectTab("verdict")}
            className={`flex items-center justify-center gap-1 py-1.5 px-2 rounded-lg font-bold transition-all cursor-pointer ${
              activeTab === "verdict" ? "bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-xs" : "text-slate-500 hover:text-slate-800 dark:text-slate-300"
            }`}
          >
            <Scale className="w-3.5 h-3.5 text-emerald-600" />
            <span>Pháp lý</span>
          </button>
        </div>
      </div>

      <div className="pt-1 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <span className="text-slate-600 dark:text-slate-300 font-medium">Chế độ hiển thị</span>
        <button
          type="button"
          onClick={onToggleTheme}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 text-xs font-semibold cursor-pointer"
        >
          {theme === "dark" ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
          <span>{theme === "dark" ? "Giao diện Tối" : "Giao diện Sáng"}</span>
        </button>
      </div>
    </div>
  );
};
