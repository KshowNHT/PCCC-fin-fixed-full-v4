import React, { useCallback, useState } from 'react';
import { X, UploadCloud, Loader2, CheckCircle2, AlertTriangle } from 'lucide-react';
import { apiFetch } from '../lib/api';
import { ProjectInfo } from '../types';

interface BlueprintUploadProps {
  sessionId: string;
  onClose: () => void;
  onApply: (extracted: Partial<ProjectInfo>) => void;
}

/**
 * Ngày 12-17 kế hoạch: "Phát triển tính năng kéo-thả (drag&drop) ... bản vẽ"
 * + "Cập nhật UI Form để hiển thị dữ liệu do AI tự động bóc tách (Autofill)".
 */
export function BlueprintUpload({ sessionId, onClose, onApply }: BlueprintUploadProps) {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState('');
  const [extracted, setExtracted] = useState<Partial<ProjectInfo> | null>(null);

  const handleFile = (f: File | null) => {
    if (!f) return;
    const okTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/webp'];
    if (!okTypes.includes(f.type)) {
      setError('Chỉ hỗ trợ file PDF, PNG, JPG hoặc WEBP.');
      return;
    }
    setError('');
    setExtracted(null);
    setFile(f);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) handleFile(e.dataTransfer.files[0]);
  }, []);

  const handleProcess = async () => {
    if (!file) return;
    setIsProcessing(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (sessionId) formData.append('session_id', sessionId);

      const res = await apiFetch('/api/ocr/extract-drawing', { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Lỗi trích xuất bản vẽ.');
      }
      const data = await res.json();
      setExtracted(data.extractedProjectInfo || {});
    } catch (e: any) {
      setError(e.message || 'Có lỗi xảy ra khi xử lý bản vẽ.');
    } finally {
      setIsProcessing(false);
    }
  };

  const fieldLabels: Record<string, string> = {
    name: 'Tên công trình', location: 'Địa điểm', investor: 'Chủ đầu tư', designer: 'Đơn vị thiết kế',
    type: 'Loại công trình', length: 'Chiều dài (m)', width: 'Chiều rộng (m)', height: 'Chiều cao (m)',
    pcccHeight: 'Chiều cao PCCC (m)', floorArea: 'Diện tích sàn (m²)', totalFloorArea: 'Tổng diện tích sàn (m²)',
    floors: 'Số tầng nổi', basements: 'Số tầng hầm', fireRating: 'Bậc chịu lửa', commercialDetails: 'Chi tiết kinh doanh',
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200">
          <h3 className="font-semibold text-slate-800">Đọc bản vẽ tự động (OCR / Vision AI)</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <p className="text-sm text-slate-500">
            Tải lên bản vẽ mặt bằng / mặt cắt / khung tên (PDF hoặc ảnh). AI sẽ tự động đọc và bóc tách
            các thông số kỹ thuật để điền vào form dự án.
          </p>

          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={onDrop}
            className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${
              isDragging ? 'border-blue-500 bg-blue-50' : 'border-slate-300 hover:border-slate-400'
            }`}
            onClick={() => document.getElementById('blueprint-file-input')?.click()}
          >
            <UploadCloud className="w-8 h-8 mx-auto text-slate-400 mb-2" />
            <p className="text-sm text-slate-600">
              {file ? file.name : 'Kéo thả file vào đây, hoặc bấm để chọn file'}
            </p>
            <input
              id="blueprint-file-input"
              type="file"
              accept=".pdf,.png,.jpg,.jpeg,.webp"
              className="hidden"
              onChange={(e) => handleFile(e.target.files?.[0] || null)}
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 rounded-md p-3">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {!extracted && (
            <button
              disabled={!file || isProcessing}
              onClick={handleProcess}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {isProcessing ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
              {isProcessing ? 'Đang đọc bản vẽ...' : 'Bắt đầu trích xuất'}
            </button>
          )}

          {extracted && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-sm text-green-700 bg-green-50 rounded-md p-3">
                <CheckCircle2 className="w-4 h-4 shrink-0" />
                <span>Đã trích xuất được {Object.keys(extracted).length} trường thông tin. Kiểm tra lại trước khi áp dụng.</span>
              </div>
              <div className="border border-slate-200 rounded-md divide-y divide-slate-100 max-h-56 overflow-y-auto">
                {Object.entries(extracted).map(([key, value]) => (
                  <div key={key} className="flex justify-between px-3 py-2 text-sm">
                    <span className="text-slate-500">{fieldLabels[key] || key}</span>
                    <span className="text-slate-800 font-medium text-right ml-4">{Array.isArray(value) ? value.join(', ') : String(value)}</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => { setExtracted(null); setFile(null); }}
                  className="flex-1 py-2 rounded-md border border-slate-300 text-sm text-slate-600 hover:bg-slate-50"
                >
                  Thử lại
                </button>
                <button
                  onClick={() => onApply(extracted)}
                  className="flex-1 py-2 rounded-md bg-green-600 text-white text-sm font-medium hover:bg-green-700"
                >
                  Áp dụng vào form dự án
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
