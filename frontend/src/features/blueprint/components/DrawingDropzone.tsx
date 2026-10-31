import React, { useRef } from "react";
import { UploadCloud, FileText, Image, X, Plus } from "lucide-react";

interface DrawingDropzoneProps {
  files: File[];
  isDragging: boolean;
  onSelectFiles: (files: FileList | File[]) => void;
  onRemoveFile: (index: number) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: () => void;
  onDrop: (e: React.DragEvent) => void;
  disabled?: boolean;
}

export const DrawingDropzone: React.FC<DrawingDropzoneProps> = ({
  files,
  isDragging,
  onSelectFiles,
  onRemoveFile,
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

  const isPdf = (name: string) => name.toLowerCase().endsWith(".pdf");

  return (
    <div className="space-y-3">
      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.webp"
        className="hidden"
        onChange={(e) => {
          if (e.target.files) {
            onSelectFiles(e.target.files);
          }
          e.target.value = "";
        }}
        disabled={disabled}
      />

      {files.length > 0 ? (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold text-slate-700">
              Danh sách bản vẽ đã chọn:{" "}
              <span className="text-brand-orange font-bold font-mono">
                {files.length}/5
              </span>
            </span>
            {files.length < 5 && !disabled && (
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-brand-orange hover:text-orange-700 bg-orange-50 hover:bg-orange-100 px-2.5 py-1 rounded-lg transition-colors cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Thêm bản vẽ</span>
              </button>
            )}
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto custom-scrollbar pr-0.5">
            {files.map((file, idx) => (
              <div
                key={`${file.name}-${idx}`}
                className="flex items-center justify-between p-2.5 bg-orange-50/50 hover:bg-orange-50 border border-orange-200/80 rounded-xl transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                      isPdf(file.name)
                        ? "bg-red-500 text-white"
                        : "bg-brand-orange text-white"
                    } shadow-xs`}
                  >
                    {isPdf(file.name) ? (
                      <FileText className="w-4 h-4" />
                    ) : (
                      <Image className="w-4 h-4" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-800 truncate">
                      {file.name}
                    </p>
                    <p className="text-[10px] text-slate-500 font-mono">
                      {formatSize(file.size)} &bull; {isPdf(file.name) ? "PDF" : "Hình ảnh"}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => onRemoveFile(idx)}
                  disabled={disabled}
                  className="p-1 text-slate-400 hover:text-red-500 rounded-lg hover:bg-white cursor-pointer transition-colors"
                  title="Xóa file này"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          {files.length < 5 && (
            <div
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={`border border-dashed rounded-xl p-3 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-brand-orange bg-orange-50"
                  : "border-slate-300 hover:border-brand-orange hover:bg-slate-50"
              }`}
            >
              <p className="text-xs text-slate-600">
                Kéo thả thêm bản vẽ vào đây, hoặc click để chọn (tối đa {5 - files.length} file nữa)
              </p>
            </div>
          )}
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
            Kéo thả cùng lúc tối đa 5 file bản vẽ vào đây, hoặc{" "}
            <span className="text-brand-orange underline">chọn từ máy tính</span>
          </p>
          <p className="text-xs text-slate-400 mt-1">
            Hỗ trợ định dạng PDF (khung tên, mặt bằng, kết cấu) hoặc ảnh PNG, JPG, WEBP (tối đa 25MB/file)
          </p>
          <div className="mt-2.5 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-100 text-[11px] text-slate-600 font-medium">
            <span>⚡ AI tự động đọc và gộp thông số từ tất cả bản vẽ</span>
          </div>
        </div>
      )}
    </div>
  );
};
