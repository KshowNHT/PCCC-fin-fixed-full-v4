import React, { useRef } from "react";
import { UploadCloud, FileText, X } from "lucide-react";

interface DrawingDropzoneProps {
  file: File | null;
  isDragging: boolean;
  onSelectFile: (file: File | null) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  disabled?: boolean;
}

export const DrawingDropzone: React.FC<DrawingDropzoneProps> = ({
  file,
  isDragging,
  onSelectFile,
  onDragOver,
  onDragLeave,
  onDrop,
  disabled = false,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={(e) => onSelectFile(e.target.files?.[0] || null)}
        disabled={disabled}
      />

      {file ? (
        <div className="flex items-center justify-between p-3.5 bg-orange-50/60 border border-orange-200 rounded-xl">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-brand-orange text-white flex items-center justify-center shrink-0 shadow-xs">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-bold text-slate-800 truncate">{file.name}</p>
              <p className="text-[11px] text-slate-500 font-mono">{formatSize(file.size)}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => onSelectFile(null)}
            disabled={disabled}
            className="p-1 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-white cursor-pointer"
            title="Bỏ chọn file"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
            isDragging
              ? "border-brand-orange bg-orange-50/70 scale-[1.01]"
              : "border-slate-200 hover:border-brand-orange/60 hover:bg-slate-50/70"
          }`}
        >
          <div className="w-12 h-12 rounded-xl bg-orange-100 text-brand-orange flex items-center justify-center mx-auto mb-3 shadow-xs">
            <UploadCloud className="w-6 h-6" />
          </div>
          <p className="text-sm font-semibold text-slate-700">
            Kéo thả file bản vẽ vào đây, hoặc <span className="text-brand-orange underline">chọn từ máy tính</span>
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Hỗ trợ định dạng PDF (khung tên, mặt bằng, mặt cắt) hoặc ảnh PNG, JPG (tối đa 25MB)
          </p>
        </div>
      )}
    </div>
  );
};

