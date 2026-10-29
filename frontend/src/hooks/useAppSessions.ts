import { useState, useRef, useCallback } from "react";
import { apiFetch, getToken, isSameAuthSession } from "../lib/api";
import { Session, ProjectInfo } from "../types";
import { parseApiErrorMessage } from "../utils/errorParser";

export function useAppSessions(onError: (msg: string) => void) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string>("");
  const [hasMoreSessions, setHasMoreSessions] = useState(false);
  const [nextOffset, setNextOffset] = useState(50);
  const [loadingHistory, setLoadingHistory] = useState(false);

  const revisions = useRef(new Map<string, string>());
  const saveQueue = useRef<Promise<void>>(Promise.resolve());
  const saveCount = useRef(0);
  const [isSaving, setIsSaving] = useState(false);
  const [hasLocalDraft, setHasLocalDraft] = useState(false);
  const [isPending, setIsPending] = useState(false);
  const abortControllerRef = useRef<AbortController | null>(null);

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
      } else {
        await createSession();
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      onError("Không tải được danh sách hồ sơ.");
    }
  }, [rememberRevisions, onError]);

  const createSession = useCallback(async () => {
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
      setHasLocalDraft(false);
    } catch {
      onError("Không thể tạo hồ sơ mới.");
    } finally {
      setIsPending(false);
    }
  }, [onError]);

  const deleteSession = useCallback(async (id: string) => {
    setIsPending(true);
    try {
      const res = await apiFetch(`/api/sessions/${id}`, {
        method: "DELETE",
        headers: revisionHeaders(id),
      });
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      setSessions((prev) => {
        const next = prev.filter((s) => s.id !== id);
        if (activeSessionId === id && next.length > 0) setActiveSessionId(next[0].id);
        return next;
      });
    } catch {
      onError("Không xóa được hồ sơ.");
    } finally {
      setIsPending(false);
    }
  }, [activeSessionId, revisionHeaders, onError]);

  const updateProject = useCallback((info: Partial<ProjectInfo>): Promise<void> => {
    setHasLocalDraft(true);
    const sid = activeSessionId;
    const token = getToken();
    if (!sid) return Promise.resolve();
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
      } catch (err: unknown) {
        if (err instanceof Error && err.name !== "AbortError") onError(err.message);
      } finally {
        saveCount.current -= 1;
        setIsSaving(saveCount.current > 0);
      }
    });

    saveQueue.current = next;
    return next;
  }, [activeSessionId, revisionHeaders, onError]);

  const triggerAppraisal = useCallback(async () => {
    const sid = activeSessionId;
    if (!sid) return;
    setIsPending(true);
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
      setHasLocalDraft(false);
      setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") onError(err.message);
    } finally {
      setIsPending(false);
      abortControllerRef.current = null;
    }
  }, [activeSessionId, revisionHeaders, onError]);

  const sendMessage = useCallback(async (text: string) => {
    const sid = activeSessionId;
    if (!sid) return;
    setIsPending(true);
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
      setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") onError(err.message);
    } finally {
      setIsPending(false);
      abortControllerRef.current = null;
    }
  }, [activeSessionId, revisionHeaders, onError]);

  const cancelPending = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const reloadActiveSession = useCallback(async () => {
    const sid = activeSessionId;
    if (!sid) return;
    setIsPending(true);
    try {
      const res = await apiFetch(`/api/sessions/${sid}`);
      if (!res.ok) throw new Error(await parseApiErrorMessage(res));
      const data: Session = await res.json();
      if (data.revision) revisions.current.set(sid, data.revision);
      setSessions((prev) => prev.map((s) => (s.id === sid ? data : s)));
      setHasLocalDraft(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể tải lại hồ sơ.";
      onError(msg);
    } finally {
      setIsPending(false);
    }
  }, [activeSessionId, onError]);

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

  return {
    sessions,
    setSessions,
    activeSessionId,
    setActiveSessionId,
    activeSession: sessions.find((s) => s.id === activeSessionId),
    hasMoreSessions,
    loadingHistory,
    isSaving,
    hasLocalDraft,
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
  };
}
