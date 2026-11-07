import { useState, useRef, useCallback } from "react";
import { apiFetch, getToken, isSameAuthSession } from "../lib/api";
import { Session, ProjectInfo } from "../types";
import { parseApiErrorMessage } from "../utils/errorParser";

export function useAppSessions(onError: (msg: string) => void) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const activeIdRef = useRef(activeSessionId);
  activeIdRef.current = activeSessionId;

  const [hasMoreSessions, setHasMoreSessions] = useState(false);
  const [nextOffset, setNextOffset] = useState(50);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const revisions = useRef(new Map<string, string>());
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const saveCount = useRef(0);
  const failedFields = useRef(new Set<string>());
  const busyRef = useRef(false);
  const localDraftRef = useRef(false);

  const [isSaving, setIsSaving] = useState(false);
  const [hasLocalDraft, setHasLocalDraft] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

  const markDraft = useCallback(() => {
    localDraftRef.current = true;
    setHasLocalDraft(true);
  }, []);

  const revisionHeaders = useCallback((sid: string) => {
    const revision = revisions.current.get(sid);
    if (!revision) throw new Error("Chưa có phiên bản hồ sơ. Vui lòng tải lại.");
    return { "If-Match": revision };
  }, []);

  const rememberRevisions = useCallback((items: Session[]) => {
    items.forEach((item) => {
      if (item.revision) revisions.current.set(item.id, item.revision);
    });
  }, []);

  const reconcileSession = useCallback(async (sid: string) => {
    const res = await apiFetch(`/api/sessions/${sid}`);
    if (!res.ok) throw new Error(await parseApiErrorMessage(res));
    const data: Session = await res.json();
    if (data.revision) revisions.current.set(sid, data.revision);
    setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
  }, []);

  const createSession = useCallback(async () => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      const res = await apiFetch("/api/sessions", {
        method: "POST",
        body: JSON.stringify({ title: `Hồ sơ kiểm duyệt #${Date.now().toString().slice(-4)}` }),
      });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const newSess: Session = await res.json();
      if (newSess.revision) revisions.current.set(newSess.id, newSess.revision);
      setSessions((prev) => [newSess, ...prev]);
      setActiveSessionId(newSess.id);
      activeIdRef.current = newSess.id;
      localDraftRef.current = false;
      setHasLocalDraft(false);
      failedFields.current.clear();
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      onError("Không thể tạo hồ sơ mới.");
    } finally {
      if (isSameAuthSession(token, getToken())) {
        busyRef.current = false;
        setIsPending(false);
      }
    }
  }, [onError]);

  const fetchSessions = useCallback(async () => {
    try {
      const res = await apiFetch("/api/sessions?limit=50&offset=0");
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: Session[] = await res.json();
      if (!Array.isArray(data)) throw new Error("Danh sách hồ sơ không hợp lệ.");
      rememberRevisions(data);
      setHasMoreSessions(data.length === 50);
      setNextOffset(50);
      if (data.length > 0) {
        setSessions(data);
        setActiveSessionId(data[0].id);
        activeIdRef.current = data[0].id;
      } else {
        await createSession();
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      onError("Không tải được danh sách hồ sơ.");
    }
  }, [rememberRevisions, createSession, onError]);

  const selectSession = useCallback(async (id: string) => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    const s = sessions.find((item) => item.id === id);
    if (s) {
      setActiveSessionId(id);
      activeIdRef.current = id;
      localDraftRef.current = false;
      setHasLocalDraft(false);
      failedFields.current.clear();
      onError("");
      busyRef.current = true;
      setIsPending(true);
      try {
        await reconcileSession(id);
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          failedFields.current.add("__sync__");
          onError(err.message || "Không tải được hồ sơ mới nhất.");
        }
      } finally {
        if (isSameAuthSession(token, getToken())) {
          busyRef.current = false;
          setIsPending(false);
        }
      }
    }
  }, [sessions, reconcileSession, onError]);

  const deleteSession = useCallback(async (id: string) => {
    if (busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      const res = await apiFetch(`/api/sessions/${id}`, {
        method: "DELETE",
        headers: revisionHeaders(id),
      });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (activeIdRef.current === id && next.length > 0) {
          setActiveSessionId(next[0].id);
          activeIdRef.current = next[0].id;
        }
        return next;
      });
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      onError("Không xóa được hồ sơ.");
    } finally {
      if (isSameAuthSession(token, getToken())) {
        busyRef.current = false;
        setIsPending(false);
      }
    }
  }, [revisionHeaders, onError]);

  const updateProject = useCallback((info: Partial<ProjectInfo>): Promise<void> => {
    markDraft();
    const sid = activeIdRef.current;
    const token = getToken();
    if (!sid || busyRef.current) return Promise.resolve();
    saveCount.current += 1;
    setIsSaving(true);

    const next = saveQueue.current.then(async () => {
      try {
        if (!isSameAuthSession(token, getToken())) return;
        const res = await apiFetch(`/api/sessions/${sid}/project?appraise=false`, {
          method: "PUT",
          body: JSON.stringify(info),
          headers: revisionHeaders(sid),
        });
        if (!res.ok) throw new Error(await parseApiErrorMessage(res));
        const data: Session = await res.json();
        if (data.revision) revisions.current.set(sid, data.revision);
        if (saveCount.current === 1) {
          setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
        }
        Object.keys(info).forEach((key) => failedFields.current.delete(key));
        if (saveCount.current === 1) {
          failedFields.current.clear();
        }
        if (activeIdRef.current === sid && saveCount.current === 1 && !failedFields.current.size) {
          onError("");
        }
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") {
          Object.keys(info).forEach((key) => failedFields.current.add(key));
          onError(err.message);
        }
      } finally {
        saveCount.current -= 1;
        setIsSaving(saveCount.current > 0);
      }
    });

    saveQueue.current = next;
    return next;
  }, [markDraft, revisionHeaders, onError]);

  const triggerAppraisal = useCallback(async () => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
    if (busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (!isSameAuthSession(operationToken, getToken())) return;
    if (failedFields.current.size) {
      busyRef.current = false;
      setIsPending(false);
      onError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Hãy sửa và lưu lại trước khi tiếp tục.");
      return;
    }
    const sid = activeIdRef.current;
    if (!sid) {
      busyRef.current = false;
      setIsPending(false);
      return;
    }
    onError("");
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await apiFetch(`/api/sessions/${sid}/project?appraise=true`, {
        method: "PUT",
        body: JSON.stringify({}),
        headers: revisionHeaders(sid),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: Session = await res.json();
      if (data.revision) revisions.current.set(sid, data.revision);
      if (data.reviewState === "reviewed") {
        localDraftRef.current = false;
        setHasLocalDraft(false);
      }
      if (activeIdRef.current === sid) {
        setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") onError(err.message);
    } finally {
      if (abortControllerRef.current === controller && isSameAuthSession(operationToken, getToken())) {
        try {
          await reconcileSession(sid);
        } catch (err: unknown) {
          if (err instanceof Error && err.name !== "AbortError") {
            failedFields.current.add("__sync__");
            onError("Chưa xác nhận được trạng thái hồ sơ trên máy chủ. Hãy tải lại trước khi tiếp tục.");
          }
        }
        busyRef.current = false;
        setIsPending(false);
        abortControllerRef.current = null;
      }
    }
  }, [revisionHeaders, reconcileSession, onError]);

  const sendMessage = useCallback(async (text: string) => {
    const sid = activeIdRef.current;
    if (!sid || busyRef.current) return;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (!isSameAuthSession(operationToken, getToken())) return;
    if (failedFields.current.size) {
      busyRef.current = false;
      setIsPending(false);
      onError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Hãy sửa và lưu lại trước khi tiếp tục.");
      return;
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const res = await apiFetch("/api/chat", {
        method: "POST",
        body: JSON.stringify({ sessionId: sid, messageText: text }),
        headers: revisionHeaders(sid),
        signal: controller.signal,
      });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: Session = await res.json();
      if (data.revision) revisions.current.set(sid, data.revision);
      if (activeIdRef.current === sid) {
        setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") onError(err.message);
    } finally {
      if (abortControllerRef.current === controller && isSameAuthSession(operationToken, getToken())) {
        try {
          await reconcileSession(sid);
        } catch (err: unknown) {
          if (err instanceof Error && err.name !== "AbortError") {
            failedFields.current.add("__sync__");
            onError("Chưa xác nhận được trạng thái hồ sơ trên máy chủ. Hãy tải lại trước khi tiếp tục.");
          }
        }
        busyRef.current = false;
        setIsPending(false);
        abortControllerRef.current = null;
      }
    }
  }, [revisionHeaders, reconcileSession, onError]);

  const cancelPending = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const reloadActiveSession = useCallback(async () => {
    const sid = activeIdRef.current;
    if (!sid || busyRef.current || saveCount.current > 0) return;
    const token = getToken();
    busyRef.current = true;
    setIsPending(true);
    try {
      await reconcileSession(sid);
      failedFields.current.clear();
      onError("");
      localDraftRef.current = false;
      setHasLocalDraft(false);
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError(err.message || "Không thể tải lại hồ sơ.");
      }
    } finally {
      if (isSameAuthSession(token, getToken())) {
        busyRef.current = false;
        setIsPending(false);
      }
    }
  }, [reconcileSession, onError]);

  const renameSession = useCallback(
    async (id: string, newName: string) => {
      const trimmed = newName.trim();
      if (!trimmed) return;
      try {
        const res = await apiFetch(`/api/sessions/${id}/project?appraise=false`, {
          method: "PUT",
          body: JSON.stringify({ name: trimmed }),
          headers: revisionHeaders(id),
        });
        if (!res.ok) throw new Error(await parseApiErrorMessage(res));
        const data: Session = await res.json();
        if (data.revision) revisions.current.set(id, data.revision);
        setSessions((prev) => prev.map((s) => (s.id === id ? data : s)));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Không thể đổi tên hồ sơ.";
        onError(msg);
      }
    },
    [revisionHeaders, onError]
  );

  const waitReadyForExport = useCallback(async (): Promise<boolean> => {
    if (busyRef.current) return false;
    const operationToken = getToken();
    busyRef.current = true;
    setIsPending(true);
    await saveQueue.current;
    if (!isSameAuthSession(operationToken, getToken())) {
      busyRef.current = false;
      setIsPending(false);
      return false;
    }
    if (failedFields.current.size || localDraftRef.current) {
      busyRef.current = false;
      setIsPending(false);
      onError("Thông số chưa kiểm duyệt hoặc chưa lưu được. Nhập xong và bấm Kiểm duyệt hồ sơ trước khi xuất.");
      return false;
    }
    busyRef.current = false;
    setIsPending(false);
    return true;
  }, [onError]);

  return {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId: selectSession,
    activeSession: sessions.find((s) => s.id === activeSessionId),
    hasMoreSessions,
    loadingHistory,
    isSaving,
    hasLocalDraft,
    markDraft,
    isPending,
    fetchSessions,
    createSession,
    deleteSession,
    renameSession,
    reloadActiveSession,
    updateProject,
    triggerAppraisal,
    sendMessage,
    cancelPending,
    revisionHeaders,
    waitReadyForExport,
  };
}
