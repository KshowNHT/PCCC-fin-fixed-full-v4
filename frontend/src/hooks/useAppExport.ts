import { useState, useCallback } from "react";
import { apiFetch } from "../lib/api";
import { Session } from "../types";

function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export function useAppExport(
  activeSession: Session | undefined,
  getRevisionHeader: (sid: string) => { "If-Match": string },
  onError: (msg: string) => void
) {
  const [isExportingDocx, setIsExportingDocx] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingJson, setIsExportingJson] = useState(false);

  const safeFilename = (activeSession?.projectInfo.name || "Cong_trinh").replace(/\s+/g, "_");

  const handleExportDocx = useCallback(async () => {
    if (!activeSession) return;
    setIsExportingDocx(true);
    try {
      const res = await apiFetch("/api/report/export", {
        method: "POST",
        body: JSON.stringify({
          sessionId: activeSession.id,
          expectedRevision: getRevisionHeader(activeSession.id)["If-Match"],
        }),
      });
      if (!res.ok) throw new Error("Không thể tạo file báo cáo Word.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${safeFilename}.docx`);
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Lỗi xuất báo cáo Word");
    } finally {
      setIsExportingDocx(false);
    }
  }, [activeSession, getRevisionHeader, safeFilename, onError]);

  const handleExportPdf = useCallback(async () => {
    if (!activeSession) return;
    setIsExportingPdf(true);
    try {
      const res = await apiFetch("/api/report/export-pdf", {
        method: "POST",
        body: JSON.stringify({
          sessionId: activeSession.id,
          expectedRevision: getRevisionHeader(activeSession.id)["If-Match"],
        }),
      });
      if (!res.ok) throw new Error("Không thể tạo file báo cáo PDF.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${safeFilename}.pdf`);
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Lỗi xuất báo cáo PDF");
    } finally {
      setIsExportingPdf(false);
    }
  }, [activeSession, getRevisionHeader, safeFilename, onError]);

  const handleExportJson = useCallback(async () => {
    if (!activeSession) return;
    setIsExportingJson(true);
    try {
      const res = await apiFetch("/api/report/export-json", {
        method: "POST",
        body: JSON.stringify({
          sessionId: activeSession.id,
          expectedRevision: getRevisionHeader(activeSession.id)["If-Match"],
        }),
      });
      if (!res.ok) throw new Error("Không thể tạo file JSON dữ liệu.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${safeFilename}.json`);
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Lỗi xuất file JSON");
    } finally {
      setIsExportingJson(false);
    }
  }, [activeSession, getRevisionHeader, safeFilename, onError]);

  return {
    isExportingDocx,
    isExportingPdf,
    isExportingJson,
    handleExportDocx,
    handleExportPdf,
    handleExportJson,
  };
}

