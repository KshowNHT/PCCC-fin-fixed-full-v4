import React, { useState } from "react";
import { Flame, User, Copy, Check } from "lucide-react";
import { ChatMessage } from "../../../types";

interface MessageItemProps {
  message: ChatMessage;
}

export const MessageItem: React.FC<MessageItemProps> = React.memo(({ message }) => {
  const isAssistant = message.sender === "assistant";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard write failures
    }
  };

  const formattedLines = message.text.split("\n").map((line, index) => {
    const trimmed = line.trim();
    if (!trimmed) {
      return <div key={`empty-${index}`} className="h-2" />;
    }
    const isBullet = trimmed.startsWith("- ") || trimmed.startsWith("• ");
    return (
      <p
        key={`line-${index}`}
        className={`leading-relaxed text-[14.5px] ${
          isBullet ? "pl-3 text-slate-800 dark:text-slate-200 font-medium" : "text-slate-900 dark:text-slate-100"
        }`}
      >
        {trimmed}
      </p>
    );
  });

  return (
    <div
      className={`group w-full flex gap-3 px-4 py-3 rounded-2xl transition-colors ${
        isAssistant
          ? "bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 shadow-xs"
          : "bg-slate-100/80 dark:bg-slate-800/80 ml-auto max-w-[85%] self-end"
      }`}
    >
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center shrink-0 text-white shadow-xs ${
          isAssistant
            ? "bg-gradient-to-br from-brand-orange to-orange-600 shadow-brand-orange/20"
            : "bg-slate-700 dark:bg-slate-600"
        }`}
      >
        {isAssistant ? <Flame className="w-4.5 h-4.5" /> : <User className="w-4.5 h-4.5" />}
      </div>

      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-bold text-slate-700 dark:text-slate-200">
            {isAssistant ? "Trợ lý AI PCCC" : "Cán bộ thẩm duyệt"}
          </span>
          <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[11px] font-mono text-slate-400 dark:text-slate-400">{message.timestamp}</span>
            <button
              type="button"
              onClick={handleCopy}
              className="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded hover:bg-slate-100 dark:hover:bg-slate-800 cursor-pointer"
              title="Sao chép nội dung"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>

        <div className="space-y-1 text-slate-800 dark:text-slate-100">{formattedLines}</div>
      </div>
    </div>
  );
});

MessageItem.displayName = "MessageItem";

