import React from "react";
import { Clock, X } from "lucide-react";
import { useInspectionLogs } from "../hooks/useInspectionLogs";
import { InspectionLogItem } from "./InspectionLogItem";

interface InspectionLogPanelProps {
  sessionId: string;
  onClose: () => void;
}

export const InspectionLogPanel: React.FC<InspectionLogPanelProps> = ({
  sessionId,
  onClose,
}) => {
  const {
    logs,
    isLoading,
    error,
    scope,
    expandedLogId,
    handleToggleExpand,
    handleChangeScope,
  } = useInspectionLogs({ sessionId });

  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[88vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 shrink-0 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-100 text-brand-orange flex items-center justify-center shadow-xs">
              <Clock className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900">
                Nhật ký Kiểm tra &amp; Lịch sử Thẩm định (Inspection Log)
              </h3>
              <p className="text-[11px] text-slate-500">
                Bấm vào từng dòng để mở rộng xem kết luận, căn cứ pháp lý và cảnh báo
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng"
            title="Đóng (Esc)"
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Error message */}
        {error && (
          <p role="alert" className="px-6 py-3 text-xs bg-red-50 text-red-700 border-b border-red-200">
            {error}
          </p>
        )}

        {/* Scope selector */}
        <div className="flex gap-2 px-6 pt-3.5 pb-2 shrink-0 bg-white border-b border-slate-100">
          <button
            type="button"
            onClick={() => handleChangeScope("session")}
            className={`text-xs px-3.5 py-1.5 rounded-xl font-medium transition-all cursor-pointer ${
              scope === "session"
                ? "bg-brand-orange text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Hồ sơ hiện tại
          </button>
          <button
            type="button"
            onClick={() => handleChangeScope("all")}
            className={`text-xs px-3.5 py-1.5 rounded-xl font-medium transition-all cursor-pointer ${
              scope === "all"
                ? "bg-brand-orange text-white shadow-xs"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            Toàn bộ hồ sơ
          </button>
        </div>

        {/* Content list */}
        <div className="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
          {isLoading ? (
            <div className="text-center text-sm text-slate-400 py-12">
              Đang tải dữ liệu nhật ký...
            </div>
          ) : logs.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-12">
              Chưa có lần kiểm tra thẩm định nào được ghi nhận.
            </div>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => (
                <InspectionLogItem
                  key={log.id}
                  log={log}
                  isExpanded={expandedLogId === log.id}
                  onToggleExpand={handleToggleExpand}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

