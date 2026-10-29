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

export function useBlueprintOcr({
  sessionId,
  onApply,
  onClose,
}: UseBlueprintOcrProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string>("");
  const [coverageNotice, setCoverageNotice] = useState<string>("");
  const [extractedData, setExtractedData] =
    useState<Partial<ProjectInfo> | null>(null);

  const handleSelectFile = useCallback((selected: File | null) => {
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError("Hệ thống chỉ hỗ trợ định dạng PDF, PNG, JPG hoặc WEBP.");
      return;
    }
    setError("");
    setExtractedData(null);
    setCoverageNotice("");
    setFile(selected);
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
      const dropped = e.dataTransfer.files?.[0];
      if (dropped) handleSelectFile(dropped);
    },
    [handleSelectFile]
  );

  const handleExtract = async () => {
    if (!file) return;
    setIsProcessing(true);
    setError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
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
        setCoverageNotice(`${pages} trang đã đọc. ${notice}`);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Có lỗi xảy ra khi xử lý bản vẽ.";
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
      const msg = err instanceof Error ? err.message : "Chưa áp dụng được dữ liệu OCR.";
      setError(msg);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setExtractedData(null);
    setError("");
    setCoverageNotice("");
  };

  return {
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
  };
}

