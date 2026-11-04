import React, { useEffect, useState, useCallback } from "react";
import { Activity, RefreshCw } from "lucide-react";
import { apiFetch, AuthUser } from "../lib/api";

export type AiHealthStatus = "loading" | "configured" | "unconfigured" | "ok" | "error";

interface AiHealthIndicatorProps {
  currentUser: AuthUser | null;
}

export const AiHealthIndicator: React.FC<AiHealthIndicatorProps> = ({ currentUser }) => {
  const isAdmin = currentUser?.role === "admin";
  const [status, setStatus] = useState<AiHealthStatus>("loading");
  const [detail, setDetail] = useState<string>("Đang kiểm tra trạng thái cấu hình Gemini AI...");
  const [isPinging, setIsPinging] = useState(false);

  const checkHealth = useCallback(async (livePing = false) => {
    if (!isAdmin) return;
    if (livePing) setIsPinging(true);
    else setStatus("loading");

    try {
      const endpoint = livePing ? "/api/health/ai?ping=true" : "/api/health/ai";
      const res = await apiFetch(endpoint);
      if (!res.ok) {
        setStatus("error");
        setDetail(`Không kiểm tra được trạng thái AI (HTTP ${res.status}).`);
        return;
      }
      const data = await res.json();
      const configured = Boolean(data.geminiApiKeyConfigured);
      if (data.status === "ok") {
        setStatus("ok");
      } else if (data.status === "error") {
        setStatus(configured ? "error" : "unconfigured");
      } else {
        setStatus(configured ? "configured" : "unconfigured");
      }
      if (typeof data.detail === "string" && data.detail.trim()) {
        setDetail(data.detail);
      }
    } catch {
      if (livePing) {
        setStatus("error");
        setDetail("Không thể kết nối tới máy chủ để kiểm tra Gemini AI.");
      } else {
        // Ignore abort or network errors silently on initial probe, show fallback state
        setStatus((prev) => (prev === "loading" ? "unconfigured" : prev));
      }
    } finally {
      setIsPinging(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin) {
      checkHealth(false);
    }
  }, [isAdmin, checkHealth]);

  if (!isAdmin) return null;

  const badgeStyles: Record<AiHealthStatus, { wrapper: string; dot: string; shortLabel: string }> = {
    loading: {
      wrapper: "border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/80 text-slate-600 dark:text-slate-300",
      dot: "bg-blue-500 animate-pulse",
      shortLabel: "AI: Đang kiểm tra...",
    },
    ok: {
      wrapper: "border-emerald-200 dark:border-emerald-800/70 bg-emerald-50/80 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300",
      dot: "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.8)]",
      shortLabel: "AI: Hoạt động",
    },
    configured: {
      wrapper: "border-emerald-200 dark:border-emerald-800/70 bg-emerald-50/80 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300",
      dot: "bg-emerald-500",
      shortLabel: "AI: Sẵn sàng",
    },
    unconfigured: {
      wrapper: "border-amber-200 dark:border-amber-800/70 bg-amber-50/80 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300",
      dot: "bg-amber-500",
      shortLabel: "AI: Chưa cấu hình",
    },
    error: {
      wrapper: "border-red-200 dark:border-red-800/70 bg-red-50/80 dark:bg-red-950/40 text-red-700 dark:text-red-300",
      dot: "bg-red-500",
      shortLabel: "AI: Lỗi kết nối",
    },
  };

  const currentStyle = badgeStyles[status];

  return (
    <button
      id="ai-health-indicator"
      data-testid="ai-health-indicator"
      data-status={status}
      type="button"
      disabled={isPinging}
      onClick={() => checkHealth(true)}
      title={`${detail} — Bấm để kiểm tra kết nối Gemini AI trực tiếp`}
      className={`inline-flex items-center gap-1.5 px-2 py-1.5 rounded-xl border text-[11px] font-bold whitespace-nowrap shrink-0 transition-all cursor-pointer shadow-xs disabled:opacity-60 ${currentStyle.wrapper}`}
    >
      <span className={`w-2 h-2 rounded-full shrink-0 ${currentStyle.dot}`} />
      <Activity className="w-3.5 h-3.5 shrink-0 hidden 2xl:inline" />
      <span className="truncate">
        <span className="sr-only 2xl:not-sr-only">Gemini </span>
        {isPinging ? "AI: Đang ping..." : currentStyle.shortLabel}
      </span>
      <RefreshCw className={`w-3 h-3 shrink-0 opacity-70 ${isPinging ? "animate-spin" : ""}`} />
    </button>
  );
};
