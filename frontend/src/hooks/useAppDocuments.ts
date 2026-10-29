import { useState, useCallback } from "react";
import { apiFetch } from "../lib/api";
import { DocumentItem } from "../types";
import { parseApiErrorMessage } from "../utils/errorParser";

export function useAppDocuments(onError: (msg: string) => void) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await apiFetch("/api/documents");
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: DocumentItem[] = await res.json();
      if (Array.isArray(data)) setDocuments(data);
    } catch {
      onError("Không tải được danh mục văn bản pháp quy.");
    }
  }, [onError]);

  const uploadDocuments = useCallback(
    async (files: File[], code: string, title: string, type: string) => {
      const formData = new FormData();
      files.forEach((file) => formData.append("file", file));
      if (files.length === 1) {
        if (code.trim()) formData.append("code", code);
        if (title.trim()) formData.append("title", title);
      }
      formData.append("type", type);

      const res = await apiFetch("/api/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: DocumentItem | DocumentItem[] = await res.json();
      await fetchDocuments();
      return Array.isArray(data) ? data : [data];
    },
    [fetchDocuments]
  );

  const deleteDocument = useCallback(
    async (id: string) => {
      try {
        const res = await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error(await parseApiErrorMessage(res));
        await fetchDocuments();
      } catch {
        onError("Không xóa được tài liệu.");
      }
    },
    [fetchDocuments, onError]
  );

  const resetDocuments = useCallback(async () => {
    try {
      const res = await apiFetch("/api/documents/reset", { method: "POST" });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      await fetchDocuments();
    } catch {
      onError("Không thể khôi phục tài liệu gốc.");
    }
  }, [fetchDocuments, onError]);

  const downloadDocument = useCallback(async (doc: DocumentItem) => {
    try {
      const res = await apiFetch(`/api/documents/${doc.id}/download?format=pdf`);
      if (!res.ok) throw new Error("Không thể tải tài liệu.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Tai_lieu_${doc.code || doc.id}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch {
      // Ignore download errors
    }
  }, []);

  return {
    documents,
    fetchDocuments,
    uploadDocuments,
    deleteDocument,
    resetDocuments,
    downloadDocument,
  };
}

