import { useEffect, useState, useCallback } from "react";
import { apiFetch } from "../../../lib/api";
import { InspectionLogEntry, InspectionLogScope } from "../types";

interface UseInspectionLogsProps {
  sessionId: string;
}

export function useInspectionLogs({ sessionId }: UseInspectionLogsProps) {
  const [logs, setLogs] = useState<InspectionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string>("");
  const [scope, setScope] = useState<InspectionLogScope>("session");
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const fetchLogs = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setError("");
      try {
        const url =
          scope === "session" && sessionId
            ? `/api/sessions/${sessionId}/inspection-logs`
            : "/api/inspection-logs";
        const res = await apiFetch(url, { signal });
        if (!res.ok) {
          throw new Error("Không tải được nhật ký kiểm tra. Vui lòng thử lại.");
        }
        const data = (await res.json()) as unknown;
        if (signal?.aborted) return;
        if (!Array.isArray(data)) {
          throw new Error("Dữ liệu nhật ký không đúng định dạng danh sách.");
        }
        setLogs(data as InspectionLogEntry[]);
      } catch (err: unknown) {
        if (signal?.aborted) return;
        const msg =
          err instanceof Error ? err.message : "Không tải được nhật ký.";
        setError(msg);
      } finally {
        if (!signal?.aborted) {
          setIsLoading(false);
        }
      }
    },
    [scope, sessionId]
  );

  useEffect(() => {
    const controller = new AbortController();
    void fetchLogs(controller.signal);
    return () => controller.abort();
  }, [fetchLogs]);

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedLogId((prev) => (prev === id ? null : id));
  }, []);

  const handleChangeScope = useCallback((newScope: InspectionLogScope) => {
    setScope(newScope);
    setExpandedLogId(null);
  }, []);

  const handleRetry = useCallback(() => {
    void fetchLogs();
  }, [fetchLogs]);

  return {
    logs,
    isLoading,
    error,
    scope,
    expandedLogId,
    handleToggleExpand,
    handleChangeScope,
    handleRetry,
  };
}

