import React, { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { MainArea } from "./components/MainArea";
import { Login } from "./components/Login";
import { BlueprintUpload } from "./components/BlueprintUpload";
import { InspectionLogPanel } from "./components/InspectionLogPanel";
import { ProjectInfo, DocumentItem, ChatMessage, ChecklistItem } from "./types";
import { apiFetch, getStoredUser, verifySession, logout, AuthUser } from "./lib/api";
import { activateCodeProtection } from "./lib/codeProtection";
import { DevToolsWarningOverlay } from "./components/DevToolsWarningOverlay";
import { LogOut, ScanLine, History } from "lucide-react";

interface Session {
  id: string;
  title: string;
  projectInfo: ProjectInfo;
  messages: ChatMessage[];
  updatedAt: string;
  checklist?: ChecklistItem[];
  isSubjectToAppraisal?: boolean;
  appraisalReason?: string;
  warnings?: string[];
}

const EMPTY_PROJECT: ProjectInfo = {
  name: "", location: "", investor: "", designer: "", stage: "", type: "",
  length: 0, width: 0, height: 0, pcccHeight: 0, floorArea: 0, totalFloorArea: 0,
  floors: 0, basements: 0, fireRating: "Bậc III", commercialDetails: "", floorFunctions: [],
};

export default function App() {
  // Trạng thái xác thực THẬT (JWT từ backend), thay cho isAuthenticated giả trước đây.
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(getStoredUser());
  const [authChecked, setAuthChecked] = useState(false);

  // FIX (bổ sung theo yêu cầu): "khoá chặn" tài khoản test truy cập DevTools
  // để xem/khai thác mã nguồn. Chỉ áp dụng cho role "staff" (tài khoản cấp
  // cho người xem thử/QA bên ngoài) — TRỪ "admin" (chính đội ngũ vận hành,
  // cần DevTools cho công việc debug thực tế của họ). Bật/tắt toàn cục qua
  // biến môi trường VITE_ENABLE_CODE_PROTECTION (mặc định TẮT — chỉ bật khi
  // build riêng cho môi trường demo/test công khai, xem .env.example).
  // Xem cảnh báo kỹ thuật đầy đủ trong lib/codeProtection.ts: đây là biện
  // pháp răn đe ở tầng trình duyệt, KHÔNG PHẢI hàng rào bảo mật tuyệt đối.
  const [isDevToolsOpen, setIsDevToolsOpen] = useState(false);
  useEffect(() => {
    const protectionEnabled = import.meta.env.VITE_ENABLE_CODE_PROTECTION === "true";
    if (!protectionEnabled || !currentUser || currentUser.role === "admin") {
      setIsDevToolsOpen(false);
      return;
    }
    const cleanup = activateCodeProtection({
      onDevToolsDetected: () => setIsDevToolsOpen(true),
      onDevToolsClosed: () => setIsDevToolsOpen(false),
    });
    return cleanup;
  }, [currentUser]);

  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isPending, setIsPending] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingJson, setIsExportingJson] = useState(false);

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [isSubjectToAppraisal, setIsSubjectToAppraisal] = useState(false);
  const [appraisalReason, setAppraisalReason] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // Tính năng mới theo kế hoạch: OCR đọc bản vẽ (Ngày 12-17) + Nhật ký kiểm tra (Ngày 9-11)
  const [isBlueprintUploadOpen, setIsBlueprintUploadOpen] = useState(false);
  const [isInspectionLogOpen, setIsInspectionLogOpen] = useState(false);

  // FIX B03 (Bao_Cao_QA_Lan_2.md): hiển thị lỗi validation từ backend (trước
  // đây bị nuốt im lặng, người dùng không biết vì sao input không được lưu).
  const [validationError, setValidationError] = useState<string>("");

  // FIX B04: "Vẫn KHÔNG có nút hủy; người dùng phải chờ hết tiến trình
  // (12-18s+)". AbortController cho phép huỷ giữa chừng request chat/thẩm
  // định đang chạy.
  const abortControllerRef = React.useRef<AbortController | null>(null);

  /** Parse lỗi 422 từ FastAPI (Pydantic) thành thông điệp tiếng Việt dễ hiểu. */
  // FIX B18 (Bao_Cao_QA_Lan_3.md — Trung bình): lỗi validate của backend
  // (Pydantic/FastAPI) luôn trả thông điệp TIẾNG ANH thô (vd: "Input should
  // be less than or equal to 200") — hiện thẳng ra UI tiếng Việt gây khó
  // hiểu cho cán bộ thẩm định. Nhãn trường tiếng Việt tương ứng từng field.
  const FIELD_LABELS_VI: Record<string, string> = {
    floors: "Số tầng nổi", basements: "Số tầng hầm", floorArea: "Diện tích xây dựng",
    totalFloorArea: "Tổng diện tích sàn", height: "Chiều cao công trình", pcccHeight: "Chiều cao PCCC",
    length: "Chiều dài", width: "Chiều rộng", fireRating: "Bậc chịu lửa", name: "Tên công trình",
    location: "Địa điểm", investor: "Chủ đầu tư", designer: "Đơn vị thiết kế", type: "Loại công trình",
    commercialDetails: "Chi tiết kinh doanh",
  };

  /** Dịch 1 thông điệp lỗi Pydantic tiếng Anh sang tiếng Việt theo mẫu
   * thường gặp nhất. Không nhận diện được thì trả về thông điệp chung
   * chung tiếng Việt — KHÔNG BAO GIỜ để lọt tiếng Anh thô ra UI. */
  const translatePydanticMessage = (msg: string, fieldLabel: string): string => {
    const le = msg.match(/Input should be less than or equal to ([\d.]+)/);
    if (le) return `${fieldLabel}: giá trị phải nhỏ hơn hoặc bằng ${le[1]}.`;
    const ge = msg.match(/Input should be greater than or equal to ([\d.]+)/);
    if (ge) return `${fieldLabel}: giá trị phải lớn hơn hoặc bằng ${ge[1]}.`;
    const lt = msg.match(/Input should be less than ([\d.]+)/);
    if (lt) return `${fieldLabel}: giá trị phải nhỏ hơn ${lt[1]}.`;
    const gt = msg.match(/Input should be greater than ([\d.]+)/);
    if (gt) return `${fieldLabel}: giá trị phải lớn hơn ${gt[1]}.`;
    const maxLen = msg.match(/String should have at most (\d+) character/);
    if (maxLen) return `${fieldLabel}: không được vượt quá ${maxLen[1]} ký tự.`;
    const minLen = msg.match(/String should have at least (\d+) character/);
    if (minLen) return `${fieldLabel}: phải có tối thiểu ${minLen[1]} ký tự.`;
    if (/Field required/i.test(msg)) return `${fieldLabel}: bắt buộc phải nhập.`;
    if (/valid number/i.test(msg)) return `${fieldLabel}: phải là một số hợp lệ.`;
    if (/valid integer/i.test(msg)) return `${fieldLabel}: phải là số nguyên hợp lệ.`;
    // Không nhận diện được mẫu câu → thông điệp chung, không lộ tiếng Anh.
    return `${fieldLabel}: dữ liệu không hợp lệ.`;
  };

  const parseApiError = async (res: Response): Promise<string> => {
    try {
      const err = await res.json();
      if (typeof err.detail === "string") return err.detail;
      if (Array.isArray(err.detail)) {
        return err.detail
          .map((d: any) => {
            const fieldKey = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : "";
            const fieldLabel = FIELD_LABELS_VI[fieldKey] || "Dữ liệu";
            return translatePydanticMessage(d.msg || "", fieldLabel);
          })
          .join(" ");
      }
    } catch {
      /* ignore parse error, dùng thông điệp mặc định bên dưới */
    }
    return "Dữ liệu nhập không hợp lệ. Vui lòng kiểm tra lại.";
  };

  const handleCancelPending = () => {
    abortControllerRef.current?.abort();
    setIsPending(false);
  };


  // Xác thực token hiện có khi tải lại trang (F5) — trước đây mất trạng thái đăng nhập khi refresh.
  useEffect(() => {
    (async () => {
      const user = await verifySession();
      setCurrentUser(user);
      setAuthChecked(true);
    })();

    const handleUnauthorized = () => setCurrentUser(null);
    window.addEventListener("pccc:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("pccc:unauthorized", handleUnauthorized);
  }, []);

  useEffect(() => {
    const handleResize = () => setIsSidebarOpen(window.innerWidth >= 1024);
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    if (currentUser) {
      fetchSessions();
      fetchDocuments();
    }
  }, [currentUser]);

  const fetchSessions = async () => {
    try {
      const res = await apiFetch("/api/sessions");
      const data = await res.json();
      if (data && data.length > 0) {
        setSessions(data);
        setActiveSessionId(data[0].id);
        syncActiveSessionStates(data[0]);
      } else {
        handleCreateSession();
      }
    } catch (e) {
      console.error("Lỗi đồng bộ danh mục phiên:", e);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await apiFetch("/api/documents");
      const data = await res.json();
      setDocuments(data);
    } catch (e) {
      console.error("Lỗi tải bộ cơ sở dữ liệu pháp quy:", e);
    }
  };

  const handleCreateSession = async () => {
    try {
      const res = await apiFetch("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ title: `Hồ sơ kiểm duyệt #${Date.now().toString().slice(-4)}` }),
      });
      const newSess = await res.json();
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      setChecklist([]);
      setIsSubjectToAppraisal(false);
      setAppraisalReason("");
      setWarnings([]);
    } catch (e) {
      console.error("Lỗi khởi tạo phiên chat mới:", e);
    }
  };

  const handleDeleteSession = async (id: string) => {
    try {
      await apiFetch(`/api/sessions/${id}`, { method: "DELETE" });
      const nextSessions = sessions.filter((s) => s.id !== id);
      setSessions(nextSessions);
      if (activeSessionId === id && nextSessions.length > 0) {
        setActiveSessionId(nextSessions[0].id);
        syncActiveSessionStates(nextSessions[0]);
      } else if (nextSessions.length === 0) {
        handleCreateSession();
      }
    } catch (e) {
      console.error("Lỗi xóa phiên:", e);
    }
  };

  const handleSelectSession = (id: string) => {
    const s = sessions.find((item) => item.id === id);
    if (s) {
      setActiveSessionId(id);
      syncActiveSessionStates(s);
    }
  };

  const syncActiveSessionStates = (sess: Session) => {
    setChecklist(sess.checklist || []);
    setIsSubjectToAppraisal(sess.isSubjectToAppraisal ?? false);
    setAppraisalReason(sess.appraisalReason || "");
    setWarnings(sess.warnings || []);
  };

  const handleSendMessage = async (text: string) => {
    if (!activeSessionId) return;
    setIsPending(true);
    // FIX B04: tạo AbortController mới cho mỗi lượt gọi, cho phép huỷ giữa chừng.
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const updatedSessions = sessions.map((s) => {
        if (s.id === activeSessionId) {
          const userMsg: ChatMessage = { id: "msg_opt_" + Date.now(), sender: "user", text, timestamp: new Date().toISOString() };
          return { ...s, messages: [...s.messages, userMsg] };
        }
        return s;
      });
      setSessions(updatedSessions);

      const res = await apiFetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, messageText: text }),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Lỗi tương tác với dịch vụ AI.");

      const data = await res.json();
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, projectInfo: data.projectInfo, messages: data.messages, updatedAt: new Date().toISOString() } : s))
      );
      setChecklist(data.checklist || []);
      setIsSubjectToAppraisal(data.isSubjectToAppraisal ?? false);
      setAppraisalReason(data.appraisalReason || "");
      setWarnings(data.warnings || []);
    } catch (e: any) {
      // FIX B04: huỷ theo yêu cầu người dùng không phải là lỗi thật, không hiện thông báo lỗi.
      if (e?.name !== "AbortError") console.error(e);
    } finally {
      setIsPending(false);
      abortControllerRef.current = null;
    }
  };

  const handleUpdateProject = async (info: Partial<ProjectInfo>) => {
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess) return;

    const previousProjectInfo = activeSess.projectInfo;
    const newProjectInfo = { ...activeSess.projectInfo, ...info };
    setSessions((prev) => prev.map((s) => (s.id === activeSessionId ? { ...s, projectInfo: newProjectInfo } : s)));
    setValidationError("");

    try {
      const res = await apiFetch(`/api/sessions/${activeSessionId}/project?appraise=false`, {
        method: "PUT",
        body: JSON.stringify(newProjectInfo),
      });
      if (res.ok) {
        const data = await res.json();
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSessionId
              ? { ...s, projectInfo: data.projectInfo, checklist: data.checklist, isSubjectToAppraisal: data.isSubjectToAppraisal, appraisalReason: data.appraisalReason, warnings: data.warnings, updatedAt: new Date().toISOString() }
              : s
          )
        );
        setChecklist(data.checklist || []);
        setIsSubjectToAppraisal(data.isSubjectToAppraisal ?? false);
        setAppraisalReason(data.appraisalReason || "");
        setWarnings(data.warnings || []);
      } else {
        // FIX B03: trước đây lỗi 422 bị nuốt im lặng, ô nhập vẫn hiển thị giá
        // trị không hợp lệ trong khi backend đã từ chối lưu — rollback UI về
        // giá trị đã lưu gần nhất trên server, kèm thông báo lý do rõ ràng.
        const message = await parseApiError(res);
        setValidationError(message);
        setSessions((prev) => prev.map((s) => (s.id === activeSessionId ? { ...s, projectInfo: previousProjectInfo } : s)));
      }
    } catch (e) {
      console.error("Lỗi đồng bộ tham số kiến trúc lên máy chủ:", e);
    }
  };

  const handleTriggerAppraisal = async () => {
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess) return;

    setIsPending(true);
    setValidationError("");
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await apiFetch(`/api/sessions/${activeSessionId}/project?appraise=true`, {
        method: "PUT",
        body: JSON.stringify(activeSess.projectInfo),
        signal: controller.signal,
      });
      if (res.ok) {
        const data = await res.json();
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSessionId
              ? { ...s, projectInfo: data.projectInfo, messages: data.messages, checklist: data.checklist, isSubjectToAppraisal: data.isSubjectToAppraisal, appraisalReason: data.appraisalReason, warnings: data.warnings, updatedAt: new Date().toISOString() }
              : s
          )
        );
        setChecklist(data.checklist || []);
        setIsSubjectToAppraisal(data.isSubjectToAppraisal ?? false);
        setAppraisalReason(data.appraisalReason || "");
        setWarnings(data.warnings || []);
      } else {
        const message = await parseApiError(res);
        setValidationError(message);
      }
    } catch (e: any) {
      if (e?.name !== "AbortError") console.error("Lỗi kích hoạt thẩm định từ máy chủ:", e);
    } finally {
      setIsPending(false);
      abortControllerRef.current = null;
    }
  };

  // OCR: áp dụng thông số bóc tách được từ bản vẽ vào form dự án đang mở (Ngày 15-17 kế hoạch: Autofill)
  const handleApplyOcrExtraction = async (extracted: Partial<ProjectInfo>) => {
    await handleUpdateProject(extracted);
    setIsBlueprintUploadOpen(false);
  };

  const handleUploadDocuments = async (files: File[], code: string, title: string, type: string): Promise<DocumentItem[]> => {
    const formData = new FormData();
    files.forEach((file) => formData.append("file", file));
    if (files.length === 1) {
      if (code.trim()) formData.append("code", code);
      if (title.trim()) formData.append("title", title);
    }
    formData.append("type", type);

    const res = await apiFetch("/api/documents/upload", { method: "POST", body: formData });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || err.error || "Lỗi tải lên văn bản pháp quy.");
    }
    const data = await res.json();
    await fetchDocuments();
    return Array.isArray(data) ? data : [data];
  };

  const handleDeleteDocument = async (id: string) => {
    try {
      await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
      await fetchDocuments();
    } catch (e) {
      console.error("Lỗi xóa tài liệu:", e);
    }
  };

  const handleResetDocuments = async () => {
    try {
      await apiFetch("/api/documents/reset", { method: "POST" });
      await fetchDocuments();
    } catch (e) {
      console.error("Lỗi khôi phục tài liệu:", e);
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleExportReport = async () => {
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) return;
    setIsExporting(true);
    try {
      const res = await apiFetch("/api/report/export", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, projectInfo: activeSess.projectInfo, checklist, conclusions: { isAppraisalRequired: isSubjectToAppraisal, reason: appraisalReason, warnings } }),
      });
      if (!res.ok) throw new Error("Lỗi quá trình tải file báo cáo.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.docx`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo thẩm định: " + e.message);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportReportPdf = async () => {
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) return;
    setIsExportingPdf(true);
    try {
      const res = await apiFetch("/api/report/export-pdf", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, projectInfo: activeSess.projectInfo, checklist, conclusions: { isAppraisalRequired: isSubjectToAppraisal, reason: appraisalReason, warnings } }),
      });
      if (!res.ok) throw new Error("Lỗi quá trình tải file báo cáo PDF.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.pdf`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo PDF: " + e.message);
    } finally {
      setIsExportingPdf(false);
    }
  };

  // Mới (Ngày 22-25 kế hoạch): xuất báo cáo JSON, bên cạnh PDF/Word đã có.
  const handleExportReportJson = async () => {
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) return;
    setIsExportingJson(true);
    try {
      const res = await apiFetch("/api/report/export-json", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, projectInfo: activeSess.projectInfo, checklist, conclusions: { isAppraisalRequired: isSubjectToAppraisal, reason: appraisalReason, warnings } }),
      });
      if (!res.ok) throw new Error("Lỗi quá trình tải file báo cáo JSON.");
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.json`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo JSON: " + e.message);
    } finally {
      setIsExportingJson(false);
    }
  };

  const handleLogout = () => {
    logout();
    setCurrentUser(null);
    setSessions([]);
    setActiveSessionId("");
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  if (!authChecked) {
    return <div className="h-screen w-full flex items-center justify-center bg-slate-50 text-slate-400 text-sm">Đang xác thực phiên đăng nhập...</div>;
  }

  if (!currentUser) {
    return <Login onLogin={(user) => setCurrentUser(user)} />;
  }

  return (
    <div className="flex flex-col h-screen bg-slate-100 overflow-hidden font-sans relative">
      {isDevToolsOpen && <DevToolsWarningOverlay />}
      {/* Thanh trên cùng: thông tin người dùng + tính năng OCR / Nhật ký kiểm tra + đăng xuất */}
      <div className="flex items-center justify-end gap-2 px-4 py-1.5 bg-white border-b border-slate-200 text-sm shrink-0 z-40">
        <button
          onClick={() => setIsBlueprintUploadOpen(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
          title="Tải bản vẽ để AI tự động đọc và điền thông số (OCR)"
        >
          <ScanLine className="w-4 h-4" />
          <span className="hidden sm:inline">Đọc bản vẽ (OCR)</span>
        </button>
        <button
          onClick={() => setIsInspectionLogOpen(true)}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-slate-600 hover:bg-slate-100 transition-colors"
          title="Xem nhật ký các lần kiểm tra đã chạy"
        >
          <History className="w-4 h-4" />
          <span className="hidden sm:inline">Nhật ký kiểm tra</span>
        </button>
        <span className="mx-1 h-4 w-px bg-slate-200" />
        <span className="text-slate-500">
          {currentUser.fullName || currentUser.username}
          <span className="ml-1.5 text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">{currentUser.role === "admin" ? "Quản trị" : "Nhân viên"}</span>
        </span>
        <button onClick={handleLogout} className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-red-500 hover:bg-red-50 transition-colors" title="Đăng xuất">
          <LogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Đăng xuất</span>
        </button>
      </div>

      {/* FIX B03: banner lỗi validation toàn cục — trước đây lỗi 422 bị nuốt
          im lặng, người dùng không biết vì sao dữ liệu không lưu được. */}
      {validationError && (
        <div className="fixed top-12 left-1/2 -translate-x-1/2 z-50 max-w-lg w-[92%] sm:w-auto bg-red-50 border border-red-300 text-red-700 text-sm rounded-lg shadow-lg px-4 py-3 flex items-start gap-2">
          <span className="flex-1">{validationError}</span>
          <button onClick={() => setValidationError("")} className="text-red-400 hover:text-red-600 font-bold leading-none">×</button>
        </div>
      )}

      <div className="flex flex-1 overflow-hidden relative">
        <Sidebar
          project={activeSession?.projectInfo || EMPTY_PROJECT}
          onUpdateProject={handleUpdateProject}
          onTriggerAppraisal={handleTriggerAppraisal}
          isPending={isPending}
          documents={documents}
          onUploadDocument={handleUploadDocuments}
          onDeleteDocument={handleDeleteDocument}
          onResetDocuments={handleResetDocuments}
          sessions={sessions.map((s) => ({ id: s.id, title: s.projectInfo.name || s.title, updatedAt: s.updatedAt }))}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
        />

        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/40 z-35 lg:hidden transition-opacity cursor-pointer" onClick={() => setIsSidebarOpen(false)} />
        )}

        <MainArea
          sessionTitle={activeSession?.projectInfo.name || activeSession?.title || "Hồ sơ Thẩm định"}
          messages={activeSession?.messages || []}
          onSendMessage={handleSendMessage}
          onTriggerAppraisal={handleTriggerAppraisal}
          isPending={isPending}
          onCancelPending={handleCancelPending}
          checklist={checklist}
          isSubjectToAppraisal={isSubjectToAppraisal}
          appraisalReason={appraisalReason}
          warnings={warnings}
          projectInfo={activeSession?.projectInfo || EMPTY_PROJECT}
          onExportReport={handleExportReport}
          isExporting={isExporting}
          onExportReportPdf={handleExportReportPdf}
          isExportingPdf={isExportingPdf}
          isSidebarOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        />
      </div>

      {isBlueprintUploadOpen && (
        <BlueprintUpload
          sessionId={activeSessionId}
          onClose={() => setIsBlueprintUploadOpen(false)}
          onApply={handleApplyOcrExtraction}
        />
      )}

      {isInspectionLogOpen && (
        <InspectionLogPanel sessionId={activeSessionId} onClose={() => setIsInspectionLogOpen(false)} />
      )}
    </div>
  );
}
