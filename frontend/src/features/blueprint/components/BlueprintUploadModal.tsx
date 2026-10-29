import React from "react";
import { X, ScanLine, Loader2, Sparkles, AlertTriangle } from "lucide-react";
import { ProjectInfo } from "../../../types";
import { useBlueprintOcr } from "../hooks/useBlueprintOcr";
import { DrawingDropzone } from "./DrawingDropzone";
import { ExtractionPreview } from "./ExtractionPreview";

interface BlueprintUploadModalProps {
  sessionId: string;
  onClose: () => void;
  onApply: (extracted: Partial<ProjectInfo>) => Promise<void>;
}

export const BlueprintUploadModal: React.FC<BlueprintUploadModalProps> = ({
  sessionId,
  onClose,
  onApply,
}) => {
  const {
    file,
    isDragging,
    isProcessing,
    error,
    coverageNotice,
    extractedData,
    handleSelectFile,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleExtract,
    handleApplyExtracted,
    handleReset,
  } = useBlueprintOcr({ sessionId, onApply, onClose });

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-100 text-brand-orange flex items-center justify-center">
              <ScanLine className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900">Bóc tách Bản vẽ Kỹ thuật (OCR / Vision AI)</h3>
              <p className="text-[11px] text-slate-500">Đọc tự động thông số từ bản vẽ PDF hoặc ảnh kiến trúc</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1 custom-scrollbar">
          <DrawingDropzone
            file={file}
            isDragging={isDragging}
            onSelectFile={handleSelectFile}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            disabled={isProcessing}
          />

          {error && (
            <div className="flex items-start gap-2 p-3 bg-red-50 text-red-700 rounded-xl text-xs border border-red-200">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {extractedData && (
            <ExtractionPreview extracted={extractedData} coverageNotice={coverageNotice} />
          )}
        </div>

        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-2.5">
          {extractedData ? (
            <>
              <button
                type="button"
                onClick={handleReset}
                disabled={isProcessing}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200/60 rounded-xl transition-all cursor-pointer"
              >
                Tải file khác
              </button>
              <button
                type="button"
                onClick={handleApplyExtracted}
                disabled={isProcessing}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-xs transition-all cursor-pointer"
              >
                {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                <span>Áp dụng vào hồ sơ dự án</span>
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold text-slate-600 hover:bg-slate-200/60 rounded-xl transition-all cursor-pointer"
              >
                Đóng
              </button>
              <button
                type="button"
                onClick={handleExtract}
                disabled={!file || isProcessing}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:bg-slate-200 text-white text-xs font-bold shadow-xs transition-all cursor-pointer disabled:cursor-not-allowed"
              >
                {isProcessing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <ScanLine className="w-3.5 h-3.5" />}
                <span>{isProcessing ? "AI đang đọc bản vẽ..." : "Bắt đầu bóc tách"}</span>
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

