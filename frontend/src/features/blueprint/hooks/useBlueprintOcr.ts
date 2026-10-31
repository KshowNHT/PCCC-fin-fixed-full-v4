import { useState, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { ProjectInfo } from "../../../types";

interface UseBlueprintOcrProps {
  sessionId: string;
  onApply: (extracted: Partial<ProjectInfo>) => Promise<void>;
  onClose: () => void;
}

interface CoverageInfo {
  pagesRead?: number;
  notice?: string;
  filesProcessed?: number;
}

interface OcrApiResponse {
  extractedProjectInfo?: Partial<ProjectInfo>;
  coverage?: CoverageInfo;
  detail?: string;
}

const ACCEPTED_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/webp",
];

const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];
const MAX_FILES = 5;

function isAcceptedFile(f: File): boolean {
  if (ACCEPTED_TYPES.includes(f.type)) return true;
  const name = f.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export function useBlueprintOcr({
  sessionId,
  onApply,
  onClose,
}: UseBlueprintOcrProps) {
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>("");
  const [coverageNotice, setCoverageNotice] = useState<string>("");
  const [extractedData, setExtractedData] =
    useState<Partial<ProjectInfo> | null>(null);

  const handleSelectFiles = useCallback(
    (selected: FileList | File[]) => {
      const incoming = Array.from(selected);
      if (incoming.length === 0) return;

      const invalid = incoming.filter((f) => !isAcceptedFile(f));
      if (invalid.length > 0) {
        setError("Hệ thống chỉ hỗ trợ file định dạng PDF, PNG, JPG hoặc WEBP.");
        return;
      }

      setError("");
      setExtractedData(null);
      setCoverageNotice("");

      setFiles((prev) => {
        // Deduplicate incoming files by name and size
        const combined = [...prev];
        for (const file of incoming) {
          const exists = combined.some(
            (c) => c.name === file.name && c.size === file.size
          );
          if (!exists) {
            combined.push(file);
          }
        }

        if (combined.length > MAX_FILES) {
          setError(
            `Hệ thống cho phép tối đa ${MAX_FILES} file bản vẽ. Đã giữ lại ${MAX_FILES} file đầu tiên.`
          );
          return combined.slice(0, MAX_FILES);
        }
        return combined;
      });
    },
    []
  );

  const handleRemoveFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setExtractedData(null);
    setCoverageNotice("");
    setError("");
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const dropped = e.dataTransfer.files;
      if (dropped && dropped.length > 0) {
        handleSelectFiles(dropped);
      }
    },
    [handleSelectFiles]
  );

  const handleExtract = async () => {
    if (files.length === 0) {
      setError("Vui lòng chọn ít nhất một file bản vẽ.");
      return;
    }
    setIsProcessing(true);
    setError("");

    try {
      const formData = new FormData();
      for (const f of files) {
        formData.append("files", f);
      }
      formData.append("file", files[0]); // Backward compatibility
      formData.append("apply_to_session", "false");
      if (sessionId) formData.append("session_id", sessionId);

      const res = await apiFetch("/api/ocr/extract-drawing", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData: OcrApiResponse = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Lỗi khi trích xuất dữ liệu bản vẽ.");
      }

      const data: OcrApiResponse = await res.json();
      setExtractedData(data.extractedProjectInfo || {});
      if (data.coverage) {
        const pages = data.coverage.pagesRead ?? 0;
        const notice = data.coverage.notice ?? "";
        setCoverageNotice(
          `${files.length} file (${pages} trang) đã xử lý. ${notice}`.trim()
        );
      }
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Có lỗi xảy ra khi xử lý bản vẽ.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleApplyExtracted = async () => {
    if (!extractedData) return;
    setIsProcessing(true);
    try {
      await onApply(extractedData);
      onClose();
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Chưa áp dụng được dữ liệu OCR.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setFiles([]);
    setExtractedData(null);
    setError("");
    setCoverageNotice("");
  };

  return {
    files,
    isDragging,
    isProcessing,
    error,
    coverageNotice,
    extractedData,
    handleSelectFiles,
    handleRemoveFile,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleExtract,
    handleApplyExtracted,
    handleReset,
  };
}
