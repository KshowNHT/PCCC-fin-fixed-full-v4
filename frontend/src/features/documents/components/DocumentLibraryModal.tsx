import React, { useState, useEffect } from "react";
import { X, BookOpen, Search, Download, Trash2, RefreshCw, Eye, Loader2, FileText } from "lucide-react";
import { DocumentItem } from "../../../types";
import { DocumentUploadForm } from "./DocumentUploadForm";
import { apiFetch } from "../../../lib/api";

interface DocumentLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  onUploadDocument: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  onDeleteDocument: (id: string) => void;
  onResetDocuments: () => void;
  onDownloadDocument?: (doc: DocumentItem) => void;
  isAdmin?: boolean;
  userRole?: string;
}

export const DocumentLibraryModal: React.FC<DocumentLibraryModalProps> = ({
  isOpen,
  onClose,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onResetDocuments,
  onDownloadDocument,
  isAdmin: isAdminProp,
  userRole,
}) => {
  const isAdmin = isAdminProp !== undefined ? isAdminProp : (userRole ? userRole === "admin" : false);
  const [search, setSearch] = useState("");
  const [isUploading, setIsUploading] = useState(false);
  const [searchResults, setSearchResults] = useState<any[] | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewTab, setPreviewTab] = useState<"pdf" | "text">("pdf");
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");

  // Tìm kiếm sâu toàn văn theo số hiệu, tiêu đề và nội dung (Ngày 3 kế hoạch)
  useEffect(() => {
    const q = search.trim();
    if (!q) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const res = await apiFetch(`/api/documents/search?q=${encodeURIComponent(q)}`);
        if (res.ok) {
          const data = await res.json();
          setSearchResults(data);
        }
      } catch {
        // Fallback to local filter
      } finally {
        setIsSearching(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [search]);

  // Nạp PDF blob stream hiển thị trực tiếp trong iframe (Ngày 3 kế hoạch)
  useEffect(() => {
    if (!previewDoc) {
      if (pdfBlobUrl) {
        window.URL.revokeObjectURL(pdfBlobUrl);
        setPdfBlobUrl(null);
      }
      return;
    }
    let active = true;
    setPdfLoading(true);
    setPdfError("");
    setPreviewTab("pdf");
    apiFetch(`/api/documents/${previewDoc.id}/download?format=pdf&inline=true`)
      .then(async (res) => {
        if (!res.ok) throw new Error("Không thể tải bản xem trước PDF.");
        const blob = await res.blob();
        if (!active) return;
        const url = window.URL.createObjectURL(blob);
        setPdfBlobUrl(url);
      })
      .catch((err) => {
        if (!active) return;
        setPdfError(err.message || "Không thể tải bản xem trước PDF.");
      })
      .finally(() => {
        if (active) setPdfLoading(false);
      });
    return () => {
      active = false;
    };
  }, [previewDoc?.id]);

  if (!isOpen) return null;

  const displayList = searchResults !== null ? searchResults : documents.filter(
    (d) =>
      !search ||
      d.code.toLowerCase().includes(search.toLowerCase()) ||
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      (d.content && d.content.toLowerCase().includes(search.toLowerCase()))
  );

  const handleUploadWrapper = async (files: File[], code: string, title: string, type: string) => {
    setIsUploading(true);
    try {
      return await onUploadDocument(files, code, title, type);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white text-slate-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center">
              <BookOpen className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900">Thư viện Cơ sở Pháp quy &amp; Tiêu chuẩn PCCC</h3>
              <p className="text-[11px] text-slate-500">Cơ sở dữ liệu tri thức RAG được AI sử dụng để thẩm duyệt</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600 rounded-lg cursor-pointer">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4 overflow-y-auto flex-1 custom-scrollbar text-slate-900">
          {isAdmin ? (
            <DocumentUploadForm onUpload={handleUploadWrapper} isUploading={isUploading} />
          ) : (
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5 text-xs text-slate-600 flex items-center justify-between gap-3">
              <div>
                <span className="font-bold text-slate-800">Chế độ xem tài liệu: </span>
                <span>Tài khoản nhân viên được phép tra cứu, đọc và tải tài liệu. Quyền tải lên, xóa hoặc khôi phục mặc định thuộc về Quản trị viên (Admin).</span>
              </div>
              <span className="text-[10px] font-bold uppercase bg-slate-200 text-slate-700 px-2 py-0.5 rounded shrink-0">Chỉ đọc</span>
            </div>
          )}

          <div className="flex items-center justify-between gap-3 pt-2">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm kiếm văn bản (QCVN, TCVN, Nghị định...)"
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange text-slate-900 placeholder:text-slate-400 font-medium"
              />
            </div>

            {isAdmin && (
              <button
                type="button"
                onClick={onResetDocuments}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-semibold cursor-pointer shrink-0"
                title="Khôi phục danh mục tài liệu tiêu chuẩn mặc định"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Khôi phục gốc</span>
              </button>
            )}
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 max-h-72 overflow-y-auto custom-scrollbar">
            {displayList.length === 0 ? (
              <div className="p-6 text-center text-slate-500 text-xs">
                {isSearching ? "Đang tìm kiếm sâu trong kho luật..." : "Không tìm thấy văn bản pháp quy phù hợp."}
              </div>
            ) : (
              displayList.map((doc) => (
                <div key={doc.id} className="flex items-center justify-between p-3 hover:bg-slate-50/70 text-xs">
                  <div className="min-w-0 pr-3 space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 font-mono">{doc.code}</span>
                      <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-100 text-slate-600 font-bold">{doc.type}</span>
                      {doc.matchType && (
                        <span className="px-1.5 py-0.2 rounded text-[9px] bg-brand-orange/10 text-brand-orange font-bold uppercase">
                          Khớp: {doc.matchType === "code" ? "Mã hiệu" : doc.matchType === "title" ? "Tiêu đề" : "Nội dung"}
                        </span>
                      )}
                    </div>
                    <p className="text-slate-700 text-[11px] truncate font-medium">{doc.title}</p>
                    {doc.snippet && (
                      <p className="text-[10.5px] text-slate-500 italic truncate bg-amber-50/60 px-1.5 py-0.5 rounded border border-amber-100/60" title={doc.snippet}>
                        "{doc.snippet}"
                      </p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      type="button"
                      onClick={() => setPreviewDoc(doc)}
                      className="p-1.5 text-slate-400 hover:text-brand-orange rounded cursor-pointer transition-colors"
                      title="Xem trực tiếp PDF"
                    >
                      <Eye className="w-4 h-4" />
                    </button>
                    {onDownloadDocument && (
                      <button type="button" onClick={() => onDownloadDocument(doc)} className="p-1.5 text-slate-400 hover:text-blue-600 rounded cursor-pointer" title="Tải PDF">
                        <Download className="w-4 h-4" />
                      </button>
                    )}
                    {isAdmin && doc.isCustom && (
                      <button type="button" onClick={() => onDeleteDocument(doc.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded cursor-pointer" title="Xóa tài liệu">
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Cửa sổ xem trực tiếp file PDF văn bản luật gốc (Ngày 3 kế hoạch) */}
      {previewDoc && (
        <div
          className="fixed inset-0 z-60 bg-black/60 backdrop-blur-xs flex items-center justify-center p-3 sm:p-5"
          onClick={() => setPreviewDoc(null)}
        >
          <div
            className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col overflow-hidden border border-slate-200 animate-in fade-in zoom-in-95 duration-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-slate-200 bg-slate-50">
              <div className="min-w-0 pr-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-brand-orange bg-brand-orange/10 px-2 py-0.5 rounded">{previewDoc.code}</span>
                  <span className="text-[10px] font-bold uppercase bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded">{previewDoc.type}</span>
                </div>
                <h3 className="font-bold text-sm text-slate-900 truncate mt-1" title={previewDoc.title}>
                  {previewDoc.title}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setPreviewDoc(null)}
                className="p-1 text-slate-400 hover:text-slate-700 rounded-lg cursor-pointer"
                title="Đóng bản xem trước"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-2 px-5 pt-2 border-b border-slate-200 bg-slate-50 text-xs font-bold">
              <button
                type="button"
                onClick={() => setPreviewTab("pdf")}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  previewTab === "pdf" ? "bg-brand-orange text-white shadow-xs" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Xem trực tiếp PDF
              </button>
              <button
                type="button"
                onClick={() => setPreviewTab("text")}
                className={`px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                  previewTab === "text" ? "bg-brand-orange text-white shadow-xs" : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                Nội dung trích lục (Text)
              </button>
            </div>

            {/* Content view */}
            <div className="p-5 flex-1 overflow-y-auto custom-scrollbar">
              {previewTab === "pdf" ? (
                pdfLoading ? (
                  <div className="flex flex-col items-center justify-center h-[480px] bg-slate-50 border border-slate-200 rounded-xl text-slate-500 text-xs">
                    <Loader2 className="w-8 h-8 animate-spin text-brand-orange mb-2" />
                    <span>Đang nạp file PDF gốc vào khung xem trực tiếp...</span>
                  </div>
                ) : pdfBlobUrl ? (
                  <iframe
                    src={pdfBlobUrl}
                    title={previewDoc.title}
                    className="w-full h-[500px] rounded-xl border border-slate-200 shadow-inner bg-slate-100"
                  />
                ) : (
                  <div className="p-8 text-center bg-red-50 border border-red-200 rounded-xl text-red-600 text-xs">
                    {pdfError || "Không tải được bản xem trước PDF."}
                  </div>
                )
              ) : (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 p-2 bg-slate-100 rounded-lg text-xs font-bold text-slate-800">
                    <FileText className="w-4 h-4 text-brand-orange" />
                    <span>Nội dung chi tiết văn bản:</span>
                  </div>
                  <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono text-slate-800 whitespace-pre-wrap max-h-[440px] overflow-y-auto custom-scrollbar leading-relaxed">
                    {previewDoc.content || "Chưa có nội dung văn bản chi tiết."}
                  </div>
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between text-xs">
              <span className="text-slate-500 text-[11px]">Trình đọc trực tiếp văn bản quy chuẩn PCCC</span>
              <div className="flex items-center gap-2">
                {onDownloadDocument && (
                  <button
                    type="button"
                    onClick={() => onDownloadDocument(previewDoc)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-brand-orange hover:bg-orange-600 text-white font-bold cursor-pointer transition-all shadow-xs"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Tải PDF về máy</span>
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

