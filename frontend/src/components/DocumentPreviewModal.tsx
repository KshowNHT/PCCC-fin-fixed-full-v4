import React, { useState, useEffect, useRef } from "react";
import { X, FileText, Download, Loader2 } from "lucide-react";
import { DocumentItem } from "../types";
import { apiFetch } from "../lib/api";

interface DocumentPreviewModalProps {
  previewDoc: DocumentItem | null;
  onClose: () => void;
  onDownload: (doc: DocumentItem) => void;
}

export function DocumentPreviewModal({
  previewDoc,
  onClose,
  onDownload
}: DocumentPreviewModalProps) {
  const [previewTab, setPreviewTab] = useState<"pdf" | "text">("pdf");
  const [pdfBlobUrl, setPdfBlobUrl] = useState<string | null>(null);
  const [pdfLoading, setPdfLoading] = useState(false);
  const [pdfError, setPdfError] = useState("");
  const currentBlobUrlRef = useRef<string | null>(null);

  // Tải trực tiếp PDF blob stream để xem inline trong iframe (Ngày 3 kế hoạch)
  useEffect(() => {
    if (!previewDoc) {
      if (currentBlobUrlRef.current) {
        window.URL.revokeObjectURL(currentBlobUrlRef.current);
        currentBlobUrlRef.current = null;
        setPdfBlobUrl(null);
      }
      return;
    }
    let active = true;
    setPdfLoading(true);
    setPdfError("");
    setPreviewTab("pdf");

    if (currentBlobUrlRef.current) {
      window.URL.revokeObjectURL(currentBlobUrlRef.current);
      currentBlobUrlRef.current = null;
      setPdfBlobUrl(null);
    }

    apiFetch(`/api/documents/${previewDoc.id}/download?format=pdf&inline=true`)
      .then(async (res) => {
        if (!res.ok) throw new Error("Không thể tải bản xem trước PDF.");
        const blob = await res.blob();
        if (!active) return;
        const url = window.URL.createObjectURL(blob);
        currentBlobUrlRef.current = url;
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
      if (currentBlobUrlRef.current) {
        window.URL.revokeObjectURL(currentBlobUrlRef.current);
        currentBlobUrlRef.current = null;
      }
    };
  }, [previewDoc?.id]);

  if (!previewDoc) return null;

  return (
    <div
      className="fixed inset-0 bg-slate-950/60 backdrop-blur-sm flex items-center justify-center p-4 md:p-6 z-50 select-none animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl w-full max-w-3xl max-h-[85vh] shadow-[0_25px_60px_-15px_rgba(0,0,0,0.35)] flex flex-col overflow-hidden border border-slate-200/60 animate-in zoom-in-95 duration-200 text-black text-left"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-150 bg-slate-50 flex items-center justify-between shrink-0">
          <div className="min-w-0 pr-4">
            <span className="inline-block bg-brand-orange/10 text-brand-orange font-black font-mono text-[11px] rounded px-2.5 py-0.5 uppercase tracking-wide mb-1.5 border border-brand-orange/20">
              {previewDoc.type || "TÀI LIỆU"}
            </span>
            <h3
              className="font-display font-black text-sm md:text-base text-black truncate"
              title={previewDoc.title}
            >
              [{previewDoc.code}] {previewDoc.title}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-black p-2 hover:bg-slate-200 rounded-xl transition-all cursor-pointer shrink-0 flex items-center justify-center"
            title="Đóng bản xem trước"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-5 text-sm font-sans select-text">
          {/* Context Metadata GRID */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-slate-50/80 border border-slate-200/80 rounded-xl p-4 text-[12.5px] font-sans">
            <div className="flex flex-col gap-0.5 sm:border-r border-slate-200/65 pr-2">
              <span className="text-slate-500 font-medium">Ký hiệu pháp lý:</span>
              <span className="font-mono text-brand-orange font-black text-sm">{previewDoc.code}</span>
            </div>
            <div className="flex flex-col gap-0.5 sm:border-r border-slate-200/65 sm:px-2">
              <span className="text-slate-500 font-medium">Loại văn bản:</span>
              <span className="text-slate-900 font-black text-sm uppercase">{previewDoc.type}</span>
            </div>
            {previewDoc.uploadedAt ? (
              <div className="flex flex-col gap-0.5 sm:pl-2">
                <span className="text-slate-500 font-medium">Ngày cập nhật:</span>
                <span className="text-slate-800 font-bold">
                  {new Date(previewDoc.uploadedAt).toLocaleDateString("vi-VN") +
                    " " +
                    new Date(previewDoc.uploadedAt).toLocaleTimeString("vi-VN", {
                      hour: "2-digit",
                      minute: "2-digit"
                    })}
                </span>
              </div>
            ) : (
              <div className="flex flex-col gap-0.5 sm:pl-2">
                <span className="text-slate-500 font-medium">Trạng thái xác thực:</span>
                <span className="text-emerald-600 font-bold flex items-center gap-1">Chính thức</span>
              </div>
            )}
          </div>

          {/* Tabs xem PDF trực tiếp vs Text bóc tách */}
          <div className="flex items-center gap-2 border-b border-slate-200 pb-1">
            <button
              type="button"
              onClick={() => setPreviewTab("pdf")}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                previewTab === "pdf"
                  ? "bg-brand-orange text-white shadow-xs"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Xem trực tiếp PDF
            </button>
            <button
              type="button"
              onClick={() => setPreviewTab("text")}
              className={`px-3 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                previewTab === "text"
                  ? "bg-brand-orange text-white shadow-xs"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              Nội dung trích lục (Text)
            </button>
          </div>

          {previewTab === "pdf" ? (
            <div className="space-y-2 flex-1 flex flex-col min-h-0 text-left">
              {pdfLoading ? (
                <div className="flex flex-col items-center justify-center h-96 bg-slate-50 border border-slate-200 rounded-xl text-slate-500 text-xs">
                  <Loader2 className="w-8 h-8 animate-spin text-brand-orange mb-2" />
                  <span>Đang nạp file PDF gốc vào khung xem trực tiếp...</span>
                </div>
              ) : pdfBlobUrl ? (
                <iframe
                  src={pdfBlobUrl}
                  title={previewDoc.title}
                  className="w-full h-[450px] rounded-xl border border-slate-200 shadow-inner bg-slate-100"
                />
              ) : (
                <div className="p-8 text-center bg-red-50 border border-red-200 rounded-xl text-red-600 text-xs">
                  {pdfError || "Không tải được bản xem trước PDF."}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-3 flex-1 flex flex-col min-h-0 text-left">
              <div className="flex items-center gap-2 text-slate-850 bg-slate-100 p-2 rounded-lg border border-slate-200">
                <FileText className="w-4 h-4 text-brand-orange shrink-0" />
                <h4 className="text-[11px] uppercase font-black tracking-wider text-slate-950">
                  Nội dung chi tiết - trích lục văn bản pháp luật:
                </h4>
              </div>
              <div className="bg-white border border-slate-200/80 rounded-xl p-4.5 text-slate-900 font-medium font-sans leading-relaxed text-[13px] whitespace-pre-wrap max-h-[380px] overflow-y-auto custom-scrollbar border-l-4 border-l-brand-orange shadow-inner text-left">
                {previewDoc.content || "Văn bản này hiện chưa có nội dung trích lục chi tiết."}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-slate-150 bg-slate-50 flex items-center justify-between text-[12px] text-slate-600 font-sans shrink-0">
          <span className="font-bold text-slate-700 hidden sm:inline">
            Cơ sở dữ liệu pháp luật phòng cháy chữa cháy
          </span>
          <div className="flex items-center gap-2.5 ml-auto sm:ml-0">
            <button
              type="button"
              onClick={() => {
                navigator.clipboard.writeText(
                  `[${previewDoc.code}] ${previewDoc.title}\n\nNội dung:\n${previewDoc.content || ""}`
                );
                alert("Đã sao chép nội dung vào bộ nhớ tạm!");
              }}
              className="px-4 py-2 border border-slate-350 bg-white hover:bg-slate-100 rounded-xl text-slate-950 font-black tracking-wide uppercase text-[11px] cursor-pointer transition-all"
            >
              Sao chép nội dung
            </button>
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                void onDownload(previewDoc);
              }}
              className="flex items-center gap-1.5 px-4 py-2 bg-brand-orange hover:bg-brand-orange/95 text-white font-black tracking-wide uppercase text-[11px] rounded-xl transition-all cursor-pointer shadow-md shadow-brand-orange/15"
            >
              <Download className="w-3.5 h-3.5" />
              Tải văn bản (PDF)
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}

