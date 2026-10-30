import React from "react";
import { FileText, ExternalLink } from "lucide-react";

interface ChatCitationBadgeProps {
  code: string;
  onClick: (code: string) => void;
}

export const ChatCitationBadge: React.FC<ChatCitationBadgeProps> = ({ code, onClick }) => {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        onClick(code);
      }}
      className="citation-tag inline-flex items-center gap-1 mx-1 px-2 py-0.5 rounded-lg bg-orange-50 hover:bg-orange-100 text-brand-orange border border-orange-200/80 font-mono text-[12px] font-bold shadow-2xs hover:shadow-xs transition-all active:scale-95 cursor-pointer select-none align-baseline"
      title={`Nhấp để mở xem trực tiếp PDF văn bản [${code}]`}
    >
      <FileText className="w-3 h-3 text-brand-orange shrink-0" />
      <span>[{code}]</span>
      <ExternalLink className="w-2.5 h-2.5 opacity-70 shrink-0" />
    </button>
  );
};

