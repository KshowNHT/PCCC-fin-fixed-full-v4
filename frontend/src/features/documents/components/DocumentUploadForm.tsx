import React, { useState, useRef } from "react";
import { Upload, Loader2, CheckCircle2, AlertCircle, FileText, Info } from "lucide-react";
import { DocumentItem } from "../../../types";

interface DocumentUploadFormProps {
  onUpload: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  isUploading: boolean;
}

export const DocumentUploadForm: React.FC<DocumentUploadFormProps> = ({ onUpload, isUploading }) => {
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("Tự động");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const parseFilenameMeta = (filename: string) => {
    const stem = filename.replace(/\.[^/.]+$/, "").replace(/[_\-]+/g, " ").trim();
    let detectedCode = "";
    let detectedType = "Tự động";

    if (/luật\s+(?:pccc|phòng\s+cháy)/i.test(stem)) {
      detectedCode = "Luật PCCC & CNCH";
      detectedType = "LUẬT";
    } else {
      const m = stem.match(/\b(TCVN|QCVN|QC|NĐ|ND|TT)\s*[:\-_/.]?\s*([0-9]+(?:\s*[:\-_/.\s]\s*[0-9]+)*)/i);
      if (m) {
        let prefix = m[1].toUpperCase();
        if (prefix === "QC") prefix = "QCVN";
        const parts = m[2].split(/[:\-_/.\s]+/).filter(Boolean);
        if (prefix === "TCVN" || prefix === "QCVN") {
          detectedType = prefix;
          const yearIdx = parts.findIndex((p) => p.length === 4 && !isNaN(Number(p)) && Number(p) >= 1950 && Number(p) <= 2050);
          if (yearIdx > 0) {
            detectedCode = `${prefix} ${parts.slice(0, yearIdx).join("-")}:${parts[yearIdx]}`;
          } else {
            detectedCode = `${prefix} ${parts.join("-")}`;
          }
        } else if (prefix === "NĐ" || prefix === "ND") {
          detectedType = "Nghị định";
          detectedCode = `${m[2]}/NĐ-CP`;
        } else if (prefix === "TT") {
          detectedType = "Thông tư";
          detectedCode = `${m[2]}/TT-BCA`;
        }
      }
    }

    return {
      code: detectedCode,
      title: stem,
      type: detectedType,
    };
  };

  const handleSelectFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files;
    if (!list || list.length === 0) return;
    setError("");
    setSuccessMsg("");
    const fileArray = Array.from(list);
    setSelectedFiles(fileArray);

    if (fileArray.length === 1) {
      const meta = parseFilenameMeta(fileArray[0].name);
      if (meta.code && !code) setCode(meta.code);
      if (meta.title && !title) setTitle(meta.title);
      if (meta.type !== "Tự động") setDocType(meta.type);
    }
  };

  const handlePerformUpload = async () => {
    if (selectedFiles.length === 0) {
      inputRef.current?.click();
      return;
    }
    setError("");
    setSuccessMsg("");
    try {
      const res = await onUpload(selectedFiles, code, title, docType);
      setCode("");
      setTitle("");
      setSelectedFiles([]);
      if (inputRef.current) inputRef.current.value = "";
      const count = Array.isArray(res) ? res.length : (res ? 1 : selectedFiles.length);
      setSuccessMsg(`Đã nạp thành công ${count} văn bản vào Thư viện RAG!`);
      setTimeout(() => setSuccessMsg(""), 6000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi tải file";
      setError(msg);
    }
  };

  return (
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold text-slate-800">Tải lên văn bản pháp quy mới (RAG Knowledge)</p>
        <span className="text-[11px] text-slate-400">Hỗ trợ: PDF có lớp chữ, Word (.docx, .doc), .txt</span>
      </div>

      <div className="p-3 bg-amber-50/90 border border-amber-200/90 rounded-xl text-xs space-y-1.5 text-amber-950">
        <div className="flex items-center gap-1.5 font-bold text-amber-900">
          <Info className="w-4 h-4 shrink-0 text-amber-600" />
          <span>Hướng dẫn chuẩn bị tài liệu &amp; Chất lượng trích xuất (DEF-03)</span>
        </div>
        <p className="text-[11px] leading-relaxed text-amber-900/90">
          • <strong>Quy chuẩn cốt lõi:</strong> Toàn bộ quy chuẩn và văn bản pháp luật nền tảng (QCVN 06:2022, TCVN, NĐ 105/2025/NĐ-CP...) đã được hệ thống mã hóa sẵn và tra cứu RAG chuẩn xác.
        </p>
        <p className="text-[11px] leading-relaxed text-amber-900/90">
          • <strong>Văn bản ngoài:</strong> Khuyến nghị ưu tiên nạp file <strong>PDF có sẵn lớp text (text layer)</strong> hoặc file Word (.docx, .doc) để thuật toán RAG bóc tách chính xác từng điều khoản.
        </p>
        <p className="text-[11px] leading-relaxed text-amber-900/90">
          • <strong>Bản vẽ kỹ thuật scan:</strong> Đối với bản vẽ thiết kế dạng scan, vui lòng sử dụng tính năng <strong>&quot;Bóc tách bản vẽ (Vision AI)&quot;</strong> tại giao diện chính thay vì nạp vào thư viện RAG này.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Mã hiệu (vd: QCVN 06:2022)"
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange text-slate-900 placeholder:text-slate-400 font-medium"
        />
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Tên văn bản / Tiêu chuẩn..."
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange text-slate-900 placeholder:text-slate-400 font-medium"
        />
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange text-slate-900 font-medium"
        >
          {["Tự động", "QCVN", "TCVN", "Nghị định", "Thông tư", "LUẬT", "Khác"].map((t) => (
            <option key={t} value={t} className="text-slate-900 bg-white">{t}</option>
          ))}
        </select>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt"
        className="hidden"
        onClick={(e) => { (e.target as HTMLInputElement).value = ""; }}
        onChange={handleSelectFiles}
      />

      {selectedFiles.length > 0 && (
        <div className="p-2.5 bg-blue-50 border border-blue-200 rounded-xl text-xs flex items-center justify-between text-blue-900">
          <span className="flex items-center gap-1.5 font-medium truncate">
            <FileText className="w-4 h-4 text-blue-600 shrink-0" />
            Đã chọn {selectedFiles.length} file: {selectedFiles.map((f) => f.name).join(", ")}
          </span>
          <button type="button" onClick={() => setSelectedFiles([])} className="text-blue-500 hover:text-blue-700 font-bold ml-2">×</button>
        </div>
      )}

      {error && (
        <div className="p-2.5 bg-red-50 border border-red-200 rounded-xl text-xs flex items-start gap-1.5 text-red-700">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded-xl text-xs flex items-center gap-1.5 text-emerald-700">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="flex items-center justify-between gap-2 pt-1">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold cursor-pointer"
        >
          {selectedFiles.length > 0 ? "Chọn file khác" : "Chọn file PDF/Word"}
        </button>

        <button
          type="button"
          disabled={isUploading || selectedFiles.length === 0}
          onClick={handlePerformUpload}
          className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-slate-900 hover:bg-black text-white text-xs font-bold transition-all cursor-pointer disabled:opacity-40"
        >
          {isUploading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
          <span>{isUploading ? "Đang nạp dữ liệu..." : "Bắt đầu tải lên"}</span>
        </button>
      </div>
    </div>
  );
};
