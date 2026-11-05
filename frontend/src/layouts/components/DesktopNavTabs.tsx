import React from "react";
import { MessageSquare, ClipboardCheck, Scale } from "lucide-react";
import { ActiveTab } from "../../types";

interface DesktopNavTabsProps {
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
}

export const DesktopNavTabs: React.FC<DesktopNavTabsProps> = ({ activeTab, onChangeTab }) => {
  return (
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
  );
};

