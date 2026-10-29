import React, { useState } from "react";
import { Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import { QUICK_PROMPTS } from "../types";

interface QuickPromptsProps {
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
}

export const QuickPrompts: React.FC<QuickPromptsProps> = React.memo(
  ({ onSelectPrompt, disabled = false }) => {
    const [collapsed, setCollapsed] = useState(false);

    if (collapsed) {
      return (
        <div className="flex justify-center px-3 py-1">
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium text-slate-500 bg-white/80 border border-slate-200 rounded-full hover:text-brand-orange hover:bg-white shadow-2xs transition-all cursor-pointer"
          >
            <Sparkles className="w-3 h-3 text-brand-orange" />
            <span>Mở gợi ý nhanh</span>
            <ChevronUp className="w-3 h-3 text-slate-400" />
          </button>
        </div>
      );
    }

    return (
      <div className="flex items-center justify-between gap-1.5 px-3 py-1.5 overflow-x-auto custom-scrollbar">
        <div className="flex items-center gap-1.5 flex-1 overflow-x-auto scrollbar-none py-0.5">
          <span className="text-[11px] font-medium text-slate-400 flex items-center gap-1 shrink-0">
            <Sparkles className="w-3 h-3 text-brand-orange" />
            <span className="hidden sm:inline">Gợi ý:</span>
          </span>
          {QUICK_PROMPTS.map((item) => (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className="inline-flex items-center px-2.5 py-1 text-[11px] font-medium text-slate-700 bg-white border border-slate-200 rounded-full hover:border-brand-orange hover:text-brand-orange hover:bg-orange-50/50 shadow-2xs shrink-0 transition-all cursor-pointer disabled:opacity-40"
            >
              <span>{item.label}</span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="p-1 text-slate-400 hover:text-slate-600 rounded-full shrink-0 cursor-pointer sm:hidden"
          title="Thu nhỏ gợi ý"
        >
          <ChevronDown className="w-3.5 h-3.5" />
        </button>
      </div>
    );
  }
);

QuickPrompts.displayName = "QuickPrompts";
