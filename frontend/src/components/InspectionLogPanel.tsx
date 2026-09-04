import React, { useEffect, useState } from 'react';
import { X, CheckCircle2, XCircle, Clock } from 'lucide-react';
import { apiFetch } from '../lib/apiService';

interface InspectionLogEntry {
  id: string;
  sessionId: string;
  triggerSource: string;
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  compliantCount: number;
  nonCompliantCount: number;
  createdAt: string;
}

interface InspectionLogPanelProps {
  sessionId: string;
  onClose: () => void;
}

const TRIGGER_LABELS: Record<string, string> = {
  chat: 'Trò chuyện AI',
  manual_appraise: 'Kích hoạt thẩm định thủ công',
  ocr_autofill: 'Tự động điền từ bản vẽ (OCR)',
};

/**
 * Ngày 9-11 kế hoạch: "Viết API lấy danh sách Log kiểm tra (Inspection
 * History)" + "Tạo bảng Data Table hiển thị lịch sử các lần kiểm tra đánh
 * giá bản vẽ" — cho phép kỹ sư truy vết kết quả AI qua thời gian.
 */
export function InspectionLogPanel({ sessionId, onClose }: InspectionLogPanelProps) {
  const [logs, setLogs] = useState<InspectionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [scope, setScope] = useState<'session' | 'all'>('session');

  useEffect(() => {
    (async () => {
      setIsLoading(true);
      try {
        const url = scope === 'session' && sessionId ? `/api/sessions/${sessionId}/inspection-logs` : '/api/inspection-logs';
        const res = await apiFetch(url);
        const data = await res.json();
        setLogs(data);
      } catch (e) {
        console.error('Lỗi tải nhật ký kiểm tra:', e);
      } finally {
        setIsLoading(false);
      }
    })();
  }, [sessionId, scope]);

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('vi-VN');
    } catch {
      return iso;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 shrink-0">
          <h3 className="font-semibold text-slate-800">Nhật ký kiểm tra (Inspection Log)</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-slate-100">
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>

        <div className="flex gap-2 px-5 pt-3 shrink-0">
          <button
            onClick={() => setScope('session')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${scope === 'session' ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-slate-100 text-slate-500'}`}
          >
            Hồ sơ hiện tại
          </button>
          <button
            onClick={() => setScope('all')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${scope === 'all' ? 'bg-blue-100 text-blue-700 font-medium' : 'bg-slate-100 text-slate-500'}`}
          >
            Toàn bộ hồ sơ
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          {isLoading ? (
            <div className="text-center text-sm text-slate-400 py-8">Đang tải nhật ký...</div>
          ) : logs.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-8">Chưa có lần kiểm tra nào được ghi nhận.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-400 border-b border-slate-100">
                  <th className="pb-2 font-medium">Thời gian</th>
                  <th className="pb-2 font-medium">Nguồn</th>
                  <th className="pb-2 font-medium">Kết luận</th>
                  <th className="pb-2 font-medium text-right">Đạt / Không đạt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {logs.map((log) => (
                  <tr key={log.id} className="align-top">
                    <td className="py-2.5 pr-2 text-slate-500 whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5 text-slate-300" />
                        {formatDate(log.createdAt)}
                      </div>
                    </td>
                    <td className="py-2.5 pr-2 text-slate-600">{TRIGGER_LABELS[log.triggerSource] || log.triggerSource}</td>
                    <td className="py-2.5 pr-2">
                      {log.isSubjectToAppraisal ? (
                        <span className="inline-flex items-center gap-1 text-red-600 text-xs font-medium">
                          <XCircle className="w-3.5 h-3.5" /> Bắt buộc thẩm duyệt
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-green-600 text-xs font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Không bắt buộc
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 text-right whitespace-nowrap">
                      <span className="text-green-600 font-medium">{log.compliantCount}</span>
                      <span className="text-slate-300 mx-1">/</span>
                      <span className="text-red-500 font-medium">{log.nonCompliantCount}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
