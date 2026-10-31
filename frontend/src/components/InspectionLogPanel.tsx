import React, { useEffect, useState } from 'react';
import {
  X,
  CheckCircle2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  BookOpen,
  FileCheck2,
  Layers,
} from 'lucide-react';
import { apiFetch } from '../lib/api';

interface LegalBasisInfo {
  lawDocument?: string;
  article?: string;
  legalExcerpt?: string;
  thresholdUsed?: string;
  appendix?: string;
}

interface ChecklistSnapshotItem {
  category?: string;
  item?: string;
  standard?: string;
  requirement?: string;
  result?: string;
  note?: string;
  reviewedBasis?: LegalBasisInfo;
}

interface InspectionLogEntry {
  id: string;
  sessionId: string;
  triggerSource: string;
  isSubjectToAppraisal: boolean;
  appraisalReason: string;
  appraisalStatus?: 'required' | 'not_required' | 'insufficient_data';
  appraisalBasis?: LegalBasisInfo | null;
  checklist?: ChecklistSnapshotItem[];
  warnings?: string[];
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
 * Ngày 5 kế hoạch: "Lưu trữ Hồ sơ Công trình & Xem Chi tiết Lịch sử".
 * Cho phép bấm vào từng dòng lịch sử kiểm tra để mở rộng (expand) xem lại
 * đầy đủ: Kết luận thẩm định, Căn cứ pháp lý và Danh sách các hạng mục cảnh báo.
 */
export function InspectionLogPanel({ sessionId, onClose }: InspectionLogPanelProps) {
  const [logs, setLogs] = useState<InspectionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [scope, setScope] = useState<'session' | 'all'>('session');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      setIsLoading(true);
      setError('');
      setLogs([]);
      try {
        const url = scope === 'session' && sessionId ? `/api/sessions/${sessionId}/inspection-logs` : '/api/inspection-logs';
        const res = await apiFetch(url, { signal: controller.signal });
        if (!res.ok) throw new Error('Không tải được nhật ký. Vui lòng thử lại.');
        const data = await res.json();
        if (controller.signal.aborted) return;
        if (!Array.isArray(data)) throw new Error('Dữ liệu nhật ký không hợp lệ.');
        setLogs(data);
      } catch (e: unknown) {
        if (!controller.signal.aborted) {
          const msg = e instanceof Error ? e.message : 'Không tải được nhật ký.';
          setError(msg);
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    })();
    return () => controller.abort();
  }, [sessionId, scope]);

  const toggleExpand = (id: string) => {
    setExpandedLogId((prev) => (prev === id ? null : id));
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleString('vi-VN');
    } catch {
      return iso;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[88vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 shrink-0 bg-slate-50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-orange-100 text-brand-orange flex items-center justify-center shadow-xs">
              <Clock className="w-4.5 h-4.5" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-slate-900">Nhật ký Kiểm tra &amp; Lịch sử Thẩm định (Inspection Log)</h3>
              <p className="text-[11px] text-slate-500">Bấm vào từng dòng để mở rộng xem kết luận, căn cứ pháp lý và cảnh báo</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200/60 transition-colors cursor-pointer" title="Đóng">
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && <p role="alert" className="px-6 py-3 text-xs bg-red-50 text-red-700 border-b border-red-200">{error}</p>}
        <div className="flex gap-2 px-6 pt-3.5 pb-2 shrink-0 bg-white border-b border-slate-100">
          <button
            onClick={() => setScope('session')}
            className={`text-xs px-3.5 py-1.5 rounded-xl font-medium transition-all cursor-pointer ${
              scope === 'session' ? 'bg-brand-orange text-white shadow-xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Hồ sơ hiện tại
          </button>
          <button
            onClick={() => setScope('all')}
            className={`text-xs px-3.5 py-1.5 rounded-xl font-medium transition-all cursor-pointer ${
              scope === 'all' ? 'bg-brand-orange text-white shadow-xs' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            Toàn bộ hồ sơ
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4 custom-scrollbar">
          {isLoading ? (
            <div className="text-center text-sm text-slate-400 py-12">Đang tải dữ liệu nhật ký...</div>
          ) : logs.length === 0 ? (
            <div className="text-center text-sm text-slate-400 py-12">Chưa có lần kiểm tra thẩm định nào được ghi nhận.</div>
          ) : (
            <div className="space-y-3">
              {logs.map((log) => {
                const isExpanded = expandedLogId === log.id;
                const nonCompliantItems = (log.checklist || []).filter(
                  (c) => c.result === 'Không đạt' || c.result === 'Khuyến nghị mạnh' || c.result === 'Khuyến nghị'
                );
                const basis = log.appraisalBasis || log.checklist?.[0]?.reviewedBasis;

                return (
                  <div
                    key={log.id}
                    className={`border rounded-xl transition-all duration-200 overflow-hidden ${
                      isExpanded
                        ? 'border-brand-orange/60 shadow-md bg-white'
                        : 'border-slate-200 hover:border-slate-300 bg-slate-50/50 hover:bg-white'
                    }`}
                  >
                    {/* Header Row (Clickable) */}
                    <div
                      onClick={() => toggleExpand(log.id)}
                      className="p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <button
                          type="button"
                          className="p-1 rounded-md text-slate-400 hover:text-brand-orange transition-colors shrink-0"
                          title={isExpanded ? 'Thu gọn' : 'Bấm để xem chi tiết'}
                        >
                          {isExpanded ? <ChevronUp className="w-4 h-4 text-brand-orange" /> : <ChevronDown className="w-4 h-4" />}
                        </button>

                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-800 flex items-center gap-1 font-mono">
                              <Clock className="w-3.5 h-3.5 text-slate-400" />
                              {formatDate(log.createdAt)}
                            </span>
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-slate-200/80 text-slate-700">
                              {TRIGGER_LABELS[log.triggerSource] || log.triggerSource}
                            </span>
                          </div>

                          <div className="mt-1 flex items-center gap-2">
                            {log.appraisalStatus === 'required' || log.isSubjectToAppraisal ? (
                              <span className="inline-flex items-center gap-1 text-red-600 text-xs font-bold">
                                <XCircle className="w-3.5 h-3.5" /> Thuộc diện thẩm duyệt PCCC
                              </span>
                            ) : log.appraisalStatus === 'not_required' ? (
                              <span className="inline-flex items-center gap-1 text-emerald-600 text-xs font-bold">
                                <CheckCircle2 className="w-3.5 h-3.5" /> Dưới ngưỡng danh mục thẩm duyệt
                              </span>
                            ) : (
                              <span className="text-amber-700 text-xs font-medium">Cần rà soát bổ sung</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div className="text-right text-xs">
                          <span className="text-emerald-600 font-bold font-mono">{log.compliantCount}</span>
                          <span className="text-slate-300 mx-1">/</span>
                          <span className="text-rose-600 font-bold font-mono">{log.nonCompliantCount}</span>
                          <p className="text-[10px] text-slate-400 font-sans">Đạt / K.Đạt</p>
                        </div>
                        <span className="text-[11px] text-brand-orange font-semibold hover:underline">
                          {isExpanded ? 'Thu gọn' : 'Xem chi tiết'}
                        </span>
                      </div>
                    </div>

                    {/* Expanded Detail Accordion */}
                    {isExpanded && (
                      <div className="p-4 pt-2 border-t border-slate-150 bg-slate-50/70 space-y-3.5 text-xs">
                        {/* 1. Kết luận thẩm định */}
                        <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                          <div className="flex items-center gap-1.5 font-bold text-slate-800 mb-1">
                            <FileCheck2 className="w-4 h-4 text-brand-orange" />
                            <span>Kết luận Thẩm định &amp; Đánh giá:</span>
                          </div>
                          <p className="text-slate-700 leading-relaxed font-sans">
                            {log.appraisalReason || 'Chưa ghi nhận lý do thẩm duyệt cụ thể.'}
                          </p>
                        </div>

                        {/* 2. Căn cứ pháp lý */}
                        {basis && (
                          <div className="bg-white p-3.5 rounded-xl border border-slate-200 shadow-2xs">
                            <div className="flex items-center gap-1.5 font-bold text-slate-800 mb-2">
                              <BookOpen className="w-4 h-4 text-blue-600" />
                              <span>Căn cứ Pháp lý &amp; Quy chuẩn Áp dụng:</span>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11.5px]">
                              {basis.lawDocument && (
                                <div className="p-2 bg-slate-50 rounded-lg">
                                  <span className="text-slate-500 font-medium">Văn bản pháp quy: </span>
                                  <span className="font-bold text-slate-800">{basis.lawDocument}</span>
                                </div>
                              )}
                              {basis.article && (
                                <div className="p-2 bg-slate-50 rounded-lg">
                                  <span className="text-slate-500 font-medium">Điều khoản: </span>
                                  <span className="font-bold text-slate-800">{basis.article}</span>
                                </div>
                              )}
                              {basis.thresholdUsed && (
                                <div className="p-2 bg-slate-50 rounded-lg sm:col-span-2">
                                  <span className="text-slate-500 font-medium">Ngưỡng áp dụng: </span>
                                  <span className="font-bold text-brand-orange">{basis.thresholdUsed}</span>
                                </div>
                              )}
                              {basis.legalExcerpt && (
                                <div className="p-2 bg-slate-50 rounded-lg sm:col-span-2 italic text-slate-600">
                                  "{basis.legalExcerpt}"
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* 3. Danh sách cảnh báo kỹ thuật */}
                        {log.warnings && log.warnings.length > 0 && (
                          <div className="bg-amber-50/80 p-3.5 rounded-xl border border-amber-200 text-amber-900">
                            <div className="flex items-center gap-1.5 font-bold text-amber-800 mb-1.5">
                              <AlertTriangle className="w-4 h-4 text-amber-600" />
                              <span>Lưu ý &amp; Cảnh báo kỹ thuật ({log.warnings.length}):</span>
                            </div>
                            <ul className="space-y-1 pl-4 list-disc text-[11.5px] leading-relaxed">
                              {log.warnings.map((w, idx) => (
                                <li key={idx}>{w}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* 4. Hạng mục Không đạt trong Checklist */}
                        {nonCompliantItems.length > 0 && (
                          <div className="bg-rose-50/60 p-3.5 rounded-xl border border-rose-200 text-rose-950">
                            <div className="flex items-center gap-1.5 font-bold text-rose-800 mb-1.5">
                              <Layers className="w-4 h-4 text-rose-600" />
                              <span>Các hạng mục chưa đạt yêu cầu ({nonCompliantItems.length}):</span>
                            </div>
                            <div className="space-y-1.5">
                              {nonCompliantItems.map((item, idx) => (
                                <div key={idx} className="bg-white/80 p-2 rounded-lg border border-rose-100 flex items-start justify-between gap-2">
                                  <div>
                                    <p className="font-bold text-slate-800">{item.item || item.category}</p>
                                    <p className="text-[11px] text-slate-500">{item.requirement || item.standard}</p>
                                    {item.note && <p className="text-[10.5px] text-rose-600 mt-0.5">{item.note}</p>}
                                  </div>
                                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700 shrink-0">
                                    {item.result}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
