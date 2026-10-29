import React, { useState } from "react";
import { X, BookOpen, Search, Download, Trash2, RefreshCw } from "lucide-react";
import { DocumentItem } from "../../../types";
import { DocumentUploadForm } from "./DocumentUploadForm";

interface DocumentLibraryModalProps {
  isOpen: boolean;
  onClose: () => void;
  documents: DocumentItem[];
  onUploadDocument: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  onDeleteDocument: (id: string) => void;
  onResetDocuments: () => void;
  onDownloadDocument?: (doc: DocumentItem) => void;
}

export const DocumentLibraryModal: React.FC<DocumentLibraryModalProps> = ({
  isOpen,
  onClose,
  documents,
  onUploadDocument,
  onDeleteDocument,
  onResetDocuments,
  onDownloadDocument,
}) => {
  const [search, setSearch] = useState("");
  const [isUploading, setIsUploading] = useState(false);

  if (!isOpen) return null;

  const filtered = documents.filter(
    (d) =>
      !search ||
      d.code.toLowerCase().includes(search.toLowerCase()) ||
      d.title.toLowerCase().includes(search.toLowerCase())
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
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
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

        <div className="p-6 space-y-4 overflow-y-auto flex-1 custom-scrollbar">
          <DocumentUploadForm onUpload={handleUploadWrapper} isUploading={isUploading} />

          <div className="flex items-center justify-between gap-3 pt-2">
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm kiếm văn bản (QCVN, TCVN, Nghị định...)"
                className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange"
              />
            </div>

            <button
              type="button"
              onClick={onResetDocuments}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-semibold cursor-pointer shrink-0"
              title="Khôi phục danh mục tài liệu tiêu chuẩn mặc định"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>Khôi phục gốc</span>
            </button>
          </div>

          <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 max-h-60 overflow-y-auto custom-scrollbar">
            {filtered.map((doc) => (
              <div key={doc.id} className="flex items-center justify-between p-3 hover:bg-slate-50/70 text-xs">
                <div className="min-w-0 pr-3 space-y-0.5">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 font-mono">{doc.code}</span>
                    <span className="px-1.5 py-0.2 rounded text-[10px] bg-slate-100 text-slate-600 font-bold">{doc.type}</span>
                  </div>
                  <p className="text-slate-600 text-[11px] truncate">{doc.title}</p>
                </div>

                <div className="flex items-center gap-1 shrink-0">
                  {onDownloadDocument && (
                    <button type="button" onClick={() => onDownloadDocument(doc)} className="p-1.5 text-slate-400 hover:text-blue-600 rounded cursor-pointer" title="Tải PDF">
                      <Download className="w-4 h-4" />
                    </button>
                  )}
                  {doc.isCustom && (
                    <button type="button" onClick={() => onDeleteDocument(doc.id)} className="p-1.5 text-slate-400 hover:text-red-600 rounded cursor-pointer" title="Xóa tài liệu">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

