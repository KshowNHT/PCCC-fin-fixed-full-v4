import React from "react";
import { CheckCircle2, XCircle, AlertCircle, HelpCircle } from "lucide-react";
import { ChecklistItem } from "../../../types";

interface ChecklistResultBadgeProps {
  result: ChecklistItem["result"];
}

export const ChecklistResultBadge: React.FC<ChecklistResultBadgeProps> = ({ result }) => {
  const text = String(result);
  if (text === "Đạt") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        Đạt
      </span>
    );
  }
  if (text === "Không đạt") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-red-50 text-red-700 border border-red-200">
        <XCircle className="w-3 h-3 text-red-600" />
        Không đạt
      </span>
    );
  }
  if (text === "Không bắt buộc" || text === "Dưới ngưỡng danh mục") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-slate-100 text-slate-600 border border-slate-200">
        <HelpCircle className="w-3 h-3 text-slate-400" />
        {text}
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-bold bg-amber-50 text-amber-700 border border-amber-200">
      <AlertCircle className="w-3 h-3 text-amber-600" />
      {text}
    </span>
  );
};

