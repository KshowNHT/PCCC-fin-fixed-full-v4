import React, { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { MainArea } from "./components/MainArea";
import { Login } from "./components/Login";
import { BlueprintUpload } from "./components/BlueprintUpload";
import { InspectionLogPanel } from "./components/InspectionLogPanel";
import { ProjectInfo, DocumentItem, ChatMessage, ChecklistItem, AppraisalBasis } from "./types";
import { apiFetch, getStoredUser, verifySession, logout, getToken, AuthUser } from "./lib/api";
import { activateCodeProtection } from "./lib/codeProtection";
import { DevToolsWarningOverlay } from "./components/DevToolsWarningOverlay";
import { LogOut, ScanLine, History } from "lucide-react";

interface Session {
  id: string;
  title: string;
  projectInfo: ProjectInfo;
  messages: ChatMessage[];
  updatedAt: string;
  revision: string;
  reviewState?: "draft" | "reviewed";
  checklist?: ChecklistItem[];
  isSubjectToAppraisal?: boolean;
  appraisalReason?: string;
  appraisalBasis?: AppraisalBasis | null;
  warnings?: string[];
}

const EMPTY_PROJECT: ProjectInfo = {
  name: "", location: "", investor: "", designer: "", stage: "", type: "",
  length: 0, width: 0, height: 0, pcccHeight: 0, floorArea: 0, totalFloorArea: 0,
  floors: 0, basements: 0, fireRating: "", commercialDetails: "", floorFunctions: [],
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
  const [nextOffset, setNextOffset] = useState(50);
  const [hasMoreSessions, setHasMoreSessions] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const activeIdRef = React.useRef(activeSessionId);
  activeIdRef.current = activeSessionId;
  const saveQueue = React.useRef<Promise<void>>(Promise.resolve());
  const saveCount = React.useRef(0);
  const failedFields = React.useRef(new Set<string>());
  const busyRef = React.useRef(false);
  const revisions = React.useRef(new Map<string, string>());
  const [formEpoch, setFormEpoch] = useState(0);
  const rememberRevisions = (items: Session[]) => {
    items.forEach(item => { if (item.revision) revisions.current.set(item.id, item.revision); });
  };
  const revisionHeaders = (sid: string) => {
    const revision = revisions.current.get(sid);
    if (!revision) throw new Error("Chưa có phiên bản hồ sơ. Tải lại hồ sơ trước khi tiếp tục.");
    return { "If-Match": revision };
  };
  const [isSaving, setIsSaving] = useState(false);
  const [hasLocalDraft, setHasLocalDraft] = useState(false);
  const localDraft = React.useRef(false);
  const markDraft = () => { localDraft.current = true; setHasLocalDraft(true); };
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isPending, setIsPending] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);
  const [isExportingJson, setIsExportingJson] = useState(false);

  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [isSubjectToAppraisal, setIsSubjectToAppraisal] = useState(false);
  const [appraisalReason, setAppraisalReason] = useState("");
  const [appraisalBasis, setAppraisalBasis] = useState<AppraisalBasis | null>(null);
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
    // Keep the operation locked until its server snapshot has been reconciled.
  };


  // Xác thực token hiện có khi tải lại trang (F5) — trước đây mất trạng thái đăng nhập khi refresh.
  useEffect(() => {
    (async () => {
      const user = await verifySession();
      setCurrentUser(user);
      setAuthChecked(true);
    })();

    const handleUnauthorized = () => handleLogout();
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
      const res = await apiFetch("/api/sessions?limit=50&offset=0");
      if (!res.ok) throw new Error(await parseApiError(res));
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error("Danh sách hồ sơ không hợp lệ.");
      rememberRevisions(data);
      setHasMoreSessions(data.length === 50);
      setNextOffset(50);
      if (data.length > 0) {
        setSessions(data);
        setActiveSessionId(data[0].id);
        syncActiveSessionStates(data[0]);
      } else {
        handleCreateSession();
      }
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setValidationError("Không tải được danh sách hồ sơ. Kiểm tra kết nối và thử lại.");
    }
  };

  const loadOlderSessions = async () => {
    if (loadingHistory || isPending) return;
    setLoadingHistory(true);
    try {
      const res = await apiFetch(`/api/sessions?limit=50&offset=${nextOffset}`);
      if (!res.ok) throw new Error(await parseApiError(res));
      const data: Session[] = await res.json();
      if (!Array.isArray(data)) throw new Error("Dữ liệu lịch sử không hợp lệ.");
      setSessions(prev => [...prev, ...data.filter(item => !prev.some(old => old.id === item.id))]);
      setNextOffset(value => value + 50);
      rememberRevisions(data);
      setHasMoreSessions(data.length === 50);
    } catch {
      setValidationError("Không tải được hồ sơ cũ. Vui lòng thử lại.");
    } finally {
      setLoadingHistory(false);
    }
  };

  const fetchDocuments = async () => {
    try {
      const res = await apiFetch("/api/documents");
      if (!res.ok) throw new Error(await parseApiError(res));
      const data = await res.json();
      if (!Array.isArray(data)) throw new Error("Danh sách tài liệu không hợp lệ.");
      setDocuments(data);
    } catch (e) {
      console.error("Lỗi tải bộ cơ sở dữ liệu pháp quy:", e);
    }
  };

  const handleCreateSession = async () => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      const res = await apiFetch("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ title: `Hồ sơ kiểm duyệt #${Date.now().toString().slice(-4)}` }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      const newSess = await res.json();
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      localDraft.current = false; setHasLocalDraft(false);
      syncActiveSessionStates(newSess);
      failedFields.current.clear();
      setIsBlueprintUploadOpen(false);
      setIsInspectionLogOpen(false);
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setValidationError("Không tạo được hồ sơ. Vui lòng thử lại.");
    } finally {
      if (token === getToken()) { busyRef.current = false; setIsPending(false); }
    }
  };

  const handleDeleteSession = async (id: string) => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      const res = await apiFetch(`/api/sessions/${id}`, { method: "DELETE", headers: revisionHeaders(id) });
      if (!res.ok) throw new Error(await parseApiError(res));
      const nextSessions = sessions.filter((s) => s.id !== id);
      setSessions(nextSessions);
      if (activeSessionId === id && nextSessions.length > 0) {
        setActiveSessionId(nextSessions[0].id);
        syncActiveSessionStates(nextSessions[0]);
      } else if (nextSessions.length === 0) {
        busyRef.current = false;
        await handleCreateSession();
      }
    } catch (e: any) {
      if (e?.name === "AbortError") return;
      setValidationError("Không xóa được hồ sơ. Vui lòng thử lại.");
    } finally {
      if (token === getToken()) { busyRef.current = false; setIsPending(false); }
    }
  };

  const handleSelectSession = async (id: string) => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    setIsBlueprintUploadOpen(false);
    setIsInspectionLogOpen(false);
    const s = sessions.find((item) => item.id === id);
    if (s) {
      setActiveSessionId(id);
      localDraft.current = false; setHasLocalDraft(false);
      syncActiveSessionStates(s);
      failedFields.current.clear();
      setValidationError("");
      activeIdRef.current = id;
      busyRef.current = true;
      setIsPending(true);
      try { await reconcileSession(id); }
      catch (e: any) {
        if (e?.name !== "AbortError") {
          failedFields.current.add("__sync__");
          setValidationError(e.message || "Không tải được hồ sơ mới nhất.");
        }
      } finally { if (token === getToken()) { busyRef.current = false; setIsPending(false); } }
    }
  };

  const syncActiveSessionStates = (sess: Session) => {
    if (sess.revision) revisions.current.set(sess.id, sess.revision);
    setChecklist(sess.checklist || []);
    setIsSubjectToAppraisal(sess.isSubjectToAppraisal ?? false);
    setAppraisalReason(sess.appraisalReason || "");
    setAppraisalBasis(sess.appraisalBasis ?? null);
    setWarnings(sess.warnings || []);
  };

  const handleSendMessage = async (text: string) => {
    if (!activeSessionId || busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (operationToken !== getToken()) return;
    if (failedFields.current.size) {
      busyRef.current = false;
      setIsPending(false);
      setValidationError("Có thông số chưa lưu được. Hãy sửa và lưu lại trước khi tiếp tục.");
      return;
    }
    // FIX B04: tạo AbortController mới cho mỗi lượt gọi, cho phép huỷ giữa chừng.
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, messageText: text }),
        headers: revisionHeaders(activeSessionId),
        signal: controller.signal,
      });

      if (!res.ok) throw new Error(await parseApiError(res));

      const data = await res.json();
      if (activeIdRef.current !== activeSessionId) return;
      setSessions((prev) =>
        prev.map((s) => (s.id === activeSessionId ? { ...s, projectInfo: data.projectInfo, messages: data.messages, checklist: data.checklist, isSubjectToAppraisal: data.isSubjectToAppraisal, appraisalReason: data.appraisalReason, appraisalBasis: data.appraisalBasis, warnings: data.warnings, updatedAt: new Date().toISOString() } : s))
      );
      setChecklist(data.checklist || []);
      setIsSubjectToAppraisal(data.isSubjectToAppraisal ?? false);
      setAppraisalReason(data.appraisalReason || "");
      setAppraisalBasis(data.appraisalBasis ?? null);
      setWarnings(data.warnings || []);
    } catch (e: any) {
      // FIX B04: huỷ theo yêu cầu người dùng không phải là lỗi thật, không hiện thông báo lỗi.
      if (e?.name !== "AbortError") setValidationError(e.message || "Kết nối thất bại. Vui lòng thử lại.");
    } finally {
      if (abortControllerRef.current === controller && operationToken === getToken()) {
        try { await reconcileSession(activeSessionId); }
        catch (e: any) {
          if (e?.name !== "AbortError") {
            failedFields.current.add("__sync__");
            setValidationError("Chưa xác nhận được trạng thái hồ sơ trên máy chủ. Hãy tải lại trước khi tiếp tục.");
          }
        }
        busyRef.current = false;
        setIsPending(false);
        abortControllerRef.current = null;
      }
    }
  };

  const handleUpdateProject = (info: Partial<ProjectInfo>): Promise<void> => {
    markDraft();
    const sid = activeIdRef.current;
    const authToken = getToken();
    if (!sid || busyRef.current) return Promise.resolve();
    saveCount.current += 1;
    setIsSaving(true);
    const next = saveQueue.current.then(async () => {
      try {
        if (authToken !== getToken()) return;
        const res = await apiFetch(`/api/sessions/${sid}/project?appraise=false`, {
          method: "PUT", body: JSON.stringify(info), headers: revisionHeaders(sid),
        });
        if (!res.ok) throw new Error(await parseApiError(res));
        const data = await res.json();
        if (data.revision) revisions.current.set(sid, data.revision);
        if (saveCount.current === 1) setSessions(prev => prev.map(s => s.id === sid ? data : s));
        Object.keys(info).forEach(key => failedFields.current.delete(key));
        if (activeIdRef.current === sid && saveCount.current === 1) {
          syncActiveSessionStates(data);
          if (!failedFields.current.size) setValidationError("");
        }
      } catch (e: any) {
        if (e?.name !== "AbortError") {
          Object.keys(info).forEach(key => failedFields.current.add(key));
          setValidationError(e.message || "Chưa lưu được thông số. Kiểm tra kết nối và nhập lại.");
        }
      } finally {
        saveCount.current -= 1;
        setIsSaving(saveCount.current > 0);
      }
    });
    saveQueue.current = next;
    return next;
  };

  const reconcileSession = async (sid: string) => {
    const res = await apiFetch(`/api/sessions/${sid}`);
    if (!res.ok) throw new Error(await parseApiError(res));
    const data = await res.json();
    setSessions(prev => prev.map(s => s.id === sid ? data : s));
    if (activeIdRef.current === sid) syncActiveSessionStates(data);
  };

  const handleReloadActiveSession = async () => {
    const sid = activeIdRef.current;
    if (!sid || busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      await reconcileSession(sid);
      failedFields.current.clear();
      setValidationError("");
      localDraft.current = false; setHasLocalDraft(false);
      setFormEpoch(value => value + 1);
    } catch (e: any) {
      if (e?.name !== "AbortError") setValidationError(e.message || "Không tải lại được hồ sơ.");
    } finally {
      if (token === getToken()) { busyRef.current = false; setIsPending(false); }
    }
  };

  const handleTriggerAppraisal = async () => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    if (busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (operationToken !== getToken()) return;
    if (failedFields.current.size) {
      busyRef.current = false;
      setIsPending(false);
      setValidationError("Có thông số chưa lưu được. Hãy sửa và lưu lại trước khi tiếp tục.");
      return;
    }
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess) { busyRef.current = false; setIsPending(false); return; }

    setIsPending(true);
    setValidationError("");
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await apiFetch(`/api/sessions/${activeSessionId}/project?appraise=true`, {
        method: "PUT",
        body: JSON.stringify({}),
        headers: revisionHeaders(activeSessionId),
        signal: controller.signal,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.reviewState === "reviewed") { localDraft.current = false; setHasLocalDraft(false); }
        if (activeIdRef.current !== activeSessionId) return;
        setSessions((prev) =>
          prev.map((s) =>
            s.id === activeSessionId
              ? { ...s, projectInfo: data.projectInfo, messages: data.messages, checklist: data.checklist, isSubjectToAppraisal: data.isSubjectToAppraisal, appraisalReason: data.appraisalReason, appraisalBasis: data.appraisalBasis, warnings: data.warnings, updatedAt: new Date().toISOString() }
              : s
          )
        );
        setChecklist(data.checklist || []);
        setIsSubjectToAppraisal(data.isSubjectToAppraisal ?? false);
        setAppraisalReason(data.appraisalReason || "");
        setAppraisalBasis(data.appraisalBasis ?? null);
        setWarnings(data.warnings || []);
      } else {
        const message = await parseApiError(res);
        setValidationError(message);
      }
    } catch (e: any) {
      if (e?.name !== "AbortError") setValidationError(e.message || "Chưa hoàn thành rà soát. Vui lòng thử lại.");
    } finally {
      if (abortControllerRef.current === controller && operationToken === getToken()) {
        try { await reconcileSession(activeSessionId); }
        catch (e: any) {
          if (e?.name !== "AbortError") {
            failedFields.current.add("__sync__");
            setValidationError("Chưa xác nhận được trạng thái hồ sơ trên máy chủ. Hãy tải lại trước khi tiếp tục.");
          }
        }
        busyRef.current = false;
        setIsPending(false);
        abortControllerRef.current = null;
      }
    }
  };

  // OCR: áp dụng thông số bóc tách được từ bản vẽ vào form dự án đang mở (Ngày 15-17 kế hoạch: Autofill)
  const handleApplyOcrExtraction = async (extracted: Partial<ProjectInfo>) => {
    await handleUpdateProject(extracted);
    if (failedFields.current.size) throw new Error("Chưa áp dụng được dữ liệu OCR. Hãy kiểm tra thông số.");
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
      const res = await apiFetch(`/api/documents/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error(await parseApiError(res));
      await fetchDocuments();
    } catch (e) {
      setValidationError("Không xóa được tài liệu. Vui lòng thử lại.");
    }
  };

  const handleResetDocuments = async () => {
    try {
      const res = await apiFetch("/api/documents/reset", { method: "POST" });
      if (!res.ok) throw new Error(await parseApiError(res));
      await fetchDocuments();
    } catch (e) {
      setValidationError("Không khôi phục được tài liệu. Vui lòng thử lại.");
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
    if (busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (operationToken !== getToken()) return;
    if (failedFields.current.size || localDraft.current) {
      busyRef.current = false;
      setIsPending(false);
      setValidationError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Nhập xong và bấm Kiểm duyệt hồ sơ trước khi xuất.");
      return;
    }
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) { busyRef.current = false; setIsPending(false); return; }
    setIsExporting(true);
    try {
      const res = await apiFetch("/api/report/export", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, expectedRevision: revisionHeaders(activeSessionId)["If-Match"] }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.docx`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo thẩm định: " + e.message);
    } finally {
      if (operationToken === getToken()) {
        busyRef.current = false;
        setIsPending(false);
        setIsExporting(false);
      }
    }
  };

  const handleExportReportPdf = async () => {
    if (busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (operationToken !== getToken()) return;
    if (failedFields.current.size || localDraft.current) {
      busyRef.current = false;
      setIsPending(false);
      setValidationError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Nhập xong và bấm Kiểm duyệt hồ sơ trước khi xuất.");
      return;
    }
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) { busyRef.current = false; setIsPending(false); return; }
    setIsExportingPdf(true);
    try {
      const res = await apiFetch("/api/report/export-pdf", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, expectedRevision: revisionHeaders(activeSessionId)["If-Match"] }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.pdf`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo PDF: " + e.message);
    } finally {
      if (operationToken === getToken()) {
        busyRef.current = false;
        setIsPending(false);
        setIsExportingPdf(false);
      }
    }
  };

  // Mới (Ngày 22-25 kế hoạch): xuất báo cáo JSON, bên cạnh PDF/Word đã có.
  const handleExportReportJson = async () => {
    if (busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (operationToken !== getToken()) return;
    if (failedFields.current.size || localDraft.current) {
      busyRef.current = false;
      setIsPending(false);
      setValidationError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Nhập xong và bấm Kiểm duyệt hồ sơ trước khi xuất.");
      return;
    }
    const activeSess = sessions.find((s) => s.id === activeSessionId);
    if (!activeSess || checklist.length === 0) { busyRef.current = false; setIsPending(false); return; }
    setIsExportingJson(true);
    try {
      const res = await apiFetch("/api/report/export-json", {
        method: "POST",
        body: JSON.stringify({ sessionId: activeSessionId, expectedRevision: revisionHeaders(activeSessionId)["If-Match"] }),
      });
      if (!res.ok) throw new Error(await parseApiError(res));
      const blob = await res.blob();
      downloadBlob(blob, `Tu_van_PCCC_${activeSess.projectInfo.name.replace(/\s+/g, "_")}.json`);
    } catch (e: any) {
      console.error(e);
      alert("Không thể tải file báo cáo JSON: " + e.message);
    } finally {
      if (operationToken === getToken()) {
        busyRef.current = false;
        setIsPending(false);
        setIsExportingJson(false);
      }
    }
  };

  const handleLogout = () => {
    abortControllerRef.current?.abort();
    logout();
    busyRef.current = false;
    failedFields.current.clear();
    revisions.current.clear();
    localDraft.current = false; setHasLocalDraft(false);
    setIsExporting(false);
    setIsExportingPdf(false);
    setIsExportingJson(false);
    setIsPending(false);
    setIsBlueprintUploadOpen(false);
    setIsInspectionLogOpen(false);
    setCurrentUser(null);
    setDocuments([]);
    setChecklist([]);
    setWarnings([]);
    setAppraisalBasis(null);
    setSessions([]);
    activeIdRef.current = "";
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
          disabled={isPending || isSaving || !activeSessionId}
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
        {isSaving && <span role="status" className="text-amber-700">Đang lưu thông số…</span>}
        <button disabled={isPending || isSaving || !activeSessionId} onClick={handleReloadActiveSession}
          title="Đọc lại dữ liệu máy chủ, bỏ các chỉnh sửa chưa lưu" className="px-2 py-1 text-slate-600">Tải lại hồ sơ</button>
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
          key={`${activeSessionId}:${formEpoch}`}
          project={activeSession?.projectInfo || EMPTY_PROJECT}
          onUpdateProject={handleUpdateProject}
          onDraftChange={markDraft}
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
          onLoadOlderSessions={hasMoreSessions ? loadOlderSessions : undefined}
          loadingHistory={loadingHistory}
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
        />

        {isSidebarOpen && (
          <div className="fixed inset-0 bg-black/40 z-35 lg:hidden transition-opacity cursor-pointer" onClick={() => setIsSidebarOpen(false)} />
        )}

        <MainArea
          sessionTitle={activeSession?.projectInfo.name || activeSession?.title || "Hồ sơ Thẩm định"}
          messages={activeSession?.messages || []}
          reviewState={hasLocalDraft ? "draft" : activeSession?.reviewState || "draft"}
          onSendMessage={handleSendMessage}
          onTriggerAppraisal={handleTriggerAppraisal}
          isPending={isPending}
          onCancelPending={handleCancelPending}
          checklist={hasLocalDraft ? [] : checklist}
          isSubjectToAppraisal={isSubjectToAppraisal}
          appraisalReason={hasLocalDraft ? "Chưa kiểm duyệt các thông số đang sửa." : appraisalReason}
          appraisalBasis={hasLocalDraft ? null : appraisalBasis}
          warnings={hasLocalDraft ? [] : warnings}
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
          key={activeSessionId}
          sessionId={activeSessionId}
          onClose={() => setIsBlueprintUploadOpen(false)}
          onApply={handleApplyOcrExtraction}
        />
      )}

      {isInspectionLogOpen && (
        <InspectionLogPanel key={activeSessionId} sessionId={activeSessionId} onClose={() => setIsInspectionLogOpen(false)} />
      )}
    </div>
  );
}
