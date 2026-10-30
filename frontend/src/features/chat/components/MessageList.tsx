import React, { useRef, useEffect } from "react";
import { Flame, ShieldCheck, FileSpreadsheet, ScanLine } from "lucide-react";
import { ChatMessage } from "../../../types";
import { MessageItem } from "./MessageItem";

interface MessageListProps {
  messages: ChatMessage[];
  isPending: boolean;
  onOpenOcrUpload: () => void;
  onOpenCitation?: (code: string) => void;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isPending,
  onOpenOcrUpload,
  onOpenCitation,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isPending]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-6 text-center max-w-xl mx-auto space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-white shadow-lg shadow-orange-500/25">
          <Flame className="w-9 h-9 animate-pulse" />
        </div>

        <div className="space-y-2">
          <h2 className="text-2xl font-bold font-display text-slate-800">
            Trợ lý AI Thẩm duyệt PCCC
          </h2>
          <p className="text-sm text-slate-500 leading-relaxed">
            Hệ thống rà soát an toàn PCCC chuyên sâu theo Nghị định 136/2020/NĐ-CP,
            Nghị định 50/2024/NĐ-CP và QCVN 06:2022/BXD.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 w-full text-left">
          <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-1.5">
            <ScanLine className="w-5 h-5 text-brand-orange" />
            <h3 className="text-xs font-bold text-slate-800">Đọc bản vẽ PDF</h3>
            <p className="text-[11px] text-slate-500">
              Kéo thả bản vẽ mặt bằng/mặt cắt để AI bóc tách thông số tự động.
            </p>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-1.5">
            <ShieldCheck className="w-5 h-5 text-emerald-600" />
            <h3 className="text-xs font-bold text-slate-800">Kiểm duyệt pháp quy</h3>
            <p className="text-[11px] text-slate-500">
              Đối soát 17-38 tiêu chí kỹ thuật và ngưỡng thẩm duyệt bắt buộc.
            </p>
          </div>

          <div className="p-3.5 rounded-xl border border-slate-200 bg-white shadow-xs space-y-1.5">
            <FileSpreadsheet className="w-5 h-5 text-blue-600" />
            <h3 className="text-xs font-bold text-slate-800">Xuất báo cáo chuẩn</h3>
            <p className="text-[11px] text-slate-500">
              Tải biên bản thẩm duyệt định dạng Word (.docx) và PDF in ấn.
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onOpenOcrUpload}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-orange-50 border border-orange-200 text-brand-orange text-xs font-bold hover:bg-orange-100/70 transition-all cursor-pointer shadow-xs"
        >
          <ScanLine className="w-4 h-4" />
          <span>Tải bản vẽ PDF / Ảnh để bắt đầu bóc tách</span>
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 custom-scrollbar">
      {messages.map((msg) => (
        <MessageItem key={msg.id} message={msg} onOpenCitation={onOpenCitation} />
      ))}

      {isPending && (
        <div className="flex items-center gap-3 px-4 py-3 bg-white border border-slate-100 rounded-2xl shadow-xs w-fit">
          <div className="w-7 h-7 rounded-lg bg-orange-100 text-brand-orange flex items-center justify-center">
            <Flame className="w-4 h-4 animate-spin" />
          </div>
          <span className="text-xs text-slate-500 font-medium">
            AI đang phân tích quy chuẩn và rà soát hồ sơ...
          </span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};

