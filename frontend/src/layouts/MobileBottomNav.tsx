import React from "react";
import { MessageSquare, ClipboardCheck, Scale } from "lucide-react";
import { ActiveTab } from "../types";

interface MobileBottomNavProps {
  activeTab: ActiveTab;
  onChangeTab: (tab: ActiveTab) => void;
  checklistCount?: number;
}

export const MobileBottomNav: React.FC<MobileBottomNavProps> = ({
  activeTab,
  onChangeTab,
  checklistCount = 0,
}) => {
  return (
    <nav className="md:hidden bg-white/95 backdrop-blur-md border-t border-slate-200 px-3 py-1.5 flex items-center justify-around shrink-0 z-30 shadow-lg">
      <button
        type="button"
        onClick={() => onChangeTab("chat")}
        className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all cursor-pointer ${
          activeTab === "chat" ? "text-brand-orange font-bold" : "text-slate-500 hover:text-slate-800"
        }`}
      >
        <MessageSquare className="w-5 h-5" />
        <span className="text-[10px]">Tư vấn AI</span>
      </button>

      <button
        type="button"
        onClick={() => onChangeTab("checklist")}
        className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all relative cursor-pointer ${
          activeTab === "checklist" ? "text-blue-600 font-bold" : "text-slate-500 hover:text-slate-800"
        }`}
      >
        <div className="relative">
          <ClipboardCheck className="w-5 h-5" />
          {checklistCount > 0 && (
            <span className="absolute -top-1 -right-2 px-1 bg-blue-600 text-white rounded-full text-[9px] font-mono font-bold leading-tight">
              {checklistCount}
            </span>
          )}
        </div>
        <span className="text-[10px]">Bảng tiêu chí</span>
      </button>

      <button
        type="button"
        onClick={() => onChangeTab("verdict")}
        className={`flex flex-col items-center gap-0.5 py-1 px-3 rounded-xl transition-all cursor-pointer ${
          activeTab === "verdict" ? "text-emerald-600 font-bold" : "text-slate-500 hover:text-slate-800"
        }`}
      >
        <Scale className="w-5 h-5" />
        <span className="text-[10px]">Căn cứ pháp lý</span>
      </button>
    </nav>
  );
};

