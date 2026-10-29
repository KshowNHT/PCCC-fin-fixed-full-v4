import React, { useState, useRef } from "react";
import { Upload, Loader2, CheckCircle2, AlertCircle, FileText } from "lucide-react";
import { DocumentItem } from "../../../types";

interface DocumentUploadFormProps {
  onUpload: (files: File[], code: string, title: string, type: string) => Promise<DocumentItem[]>;
  isUploading: boolean;
}

export const DocumentUploadForm: React.FC<DocumentUploadFormProps> = ({ onUpload, isUploading }) => {
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [docType, setDocType] = useState("TCVN");
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSelectFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const list = e.target.files;
    if (!list || list.length === 0) return;
    setError("");
    setSuccessMsg("");
    setSelectedFiles(Array.from(list));
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
      setSuccessMsg(`Đã nạp thành công ${res.length} văn bản vào Thư viện RAG!`);
      setTimeout(() => setSuccessMsg(""), 4000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Lỗi tải file";
      setError(msg);
    }
  };

  return (
    <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-bold text-slate-800">Tải lên văn bản pháp quy mới (RAG Knowledge)</p>
        <span className="text-[11px] text-slate-400">Hỗ trợ: PDF có lớp chữ, Word (.docx), .txt</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
        <input
          type="text"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Mã hiệu (vd: QCVN 06:2022)"
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange"
        />
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="Tên văn bản / Tiêu chuẩn..."
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange"
        />
        <select
          value={docType}
          onChange={(e) => setDocType(e.target.value)}
          className="px-3 py-1.5 bg-white border border-slate-200 rounded-xl text-xs outline-none focus:border-brand-orange"
        >
          {["TCVN", "QCVN", "Nghị định", "Thông tư", "LUẬT", "Khác"].map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      <input
        ref={inputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.txt"
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
