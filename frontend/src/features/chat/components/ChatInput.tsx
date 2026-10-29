import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Square, Paperclip, ScanLine } from "lucide-react";

interface ChatInputProps {
  onSendMessage: (text: string) => void;
  isPending: boolean;
  onCancelPending?: () => void;
  onOpenOcrUpload: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  isPending,
  onCancelPending,
  onOpenOcrUpload,
}) => {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!isPending) {
      textareaRef.current?.focus();
    }
  }, [isPending]);

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || isPending) return;
    onSendMessage(trimmed);
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-4 pt-1">
      <form
        onSubmit={handleSubmit}
        className="relative bg-white border border-slate-200 focus-within:border-brand-orange/60 focus-within:ring-2 focus-within:ring-brand-orange/15 rounded-2xl shadow-sm transition-all"
      >
        <div className="flex items-end gap-2 p-2.5">
          <button
            type="button"
            onClick={onOpenOcrUpload}
            className="p-2 text-slate-500 hover:text-brand-orange hover:bg-orange-50/60 rounded-xl transition-colors cursor-pointer shrink-0"
            title="Tải bản vẽ PDF / Ảnh để AI tự động bóc tách (OCR)"
          >
            <ScanLine className="w-5 h-5" />
          </button>

          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder="Hỏi về quy chuẩn PCCC, quy mô công trình, hoặc yêu cầu thẩm duyệt..."
            className="flex-1 max-h-40 py-1.5 px-2 bg-transparent text-slate-900 placeholder:text-slate-400 text-sm outline-none resize-none font-sans leading-relaxed custom-scrollbar"
          />

          {isPending ? (
            <button
              type="button"
              onClick={onCancelPending}
              className="p-2 rounded-xl bg-red-500 hover:bg-red-600 text-white transition-all cursor-pointer shrink-0 shadow-xs"
              title="Dừng tiến trình hiện tại"
            >
              <Square className="w-4 h-4 fill-white" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!text.trim()}
              className="p-2 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:bg-slate-200 text-white transition-all cursor-pointer disabled:cursor-not-allowed shrink-0 shadow-xs"
              title="Gửi câu hỏi"
            >
              <ArrowUp className="w-4 h-4 stroke-[2.5]" />
            </button>
          )}
        </div>
      </form>

      <p className="text-[11px] text-center text-slate-400 mt-2 font-mono">
        Hệ thống sàng lọc sơ bộ theo NĐ 136/2020 &amp; QCVN 06:2022. Cần kỹ sư xác nhận kết quả trước khi nghiệm thu.
      </p>
    </div>
  );
};

