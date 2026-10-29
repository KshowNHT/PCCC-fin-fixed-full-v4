import React from "react";
import { Plus, BookOpen, History, Users, KeyRound, LogOut, Flame, PanelLeftClose } from "lucide-react";
import { AuthUser } from "../lib/api";
import { SessionListItem } from "./SessionListItem";

interface SessionSummary {
  id: string;
  title: string;
  updatedAt: string;
}

interface AppSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  sessions: SessionSummary[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onCreateSession: () => void;
  onDeleteSession: (id: string) => void;
  onRenameSession?: (id: string, newTitle: string) => void;
  onLoadOlderSessions?: () => void;
  loadingHistory?: boolean;
  currentUser: AuthUser;
  onOpenDocuments: () => void;
  onOpenInspectionLog: () => void;
  onOpenUserManagement: () => void;
  onLogout: () => void;
  disabled?: boolean;
}

export const AppSidebar: React.FC<AppSidebarProps> = ({
  isOpen,
  onToggle,
  sessions,
  activeSessionId,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  onLoadOlderSessions,
  loadingHistory,
  currentUser,
  onOpenDocuments,
  onOpenInspectionLog,
  onOpenUserManagement,
  onLogout,
  disabled = false,
}) => {
  return (
    <aside
      className={`fixed lg:relative inset-y-0 left-0 z-40 flex flex-col h-full bg-slate-900 text-slate-200 transition-all duration-250 ease-in-out border-r border-slate-800 shrink-0 ${
        isOpen ? "w-64 translate-x-0" : "-translate-x-full lg:translate-x-0 lg:w-0 lg:overflow-hidden lg:border-r-0"
      }`}
    >
      <div className="p-3.5 flex items-center justify-between border-b border-slate-800">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-orange-500 to-amber-500 flex items-center justify-center text-white shrink-0 shadow-xs">
            <Flame className="w-4.5 h-4.5" />
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-xs text-white truncate font-display">AI Expert PCCC</h1>
            <p className="text-[10px] text-slate-400 font-mono">Phiên bản v11.3</p>
          </div>
        </div>
        <button type="button" onClick={onToggle} className="p-1 text-slate-400 hover:text-white rounded-lg cursor-pointer lg:hidden">
          <PanelLeftClose className="w-4.5 h-4.5" />
        </button>
      </div>

      <div className="p-3">
        <button
          type="button"
          disabled={disabled}
          onClick={onCreateSession}
          className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl bg-brand-orange hover:bg-orange-600 disabled:opacity-50 text-white text-xs font-bold shadow-xs transition-all cursor-pointer"
        >
          <Plus className="w-4 h-4" />
          <span>Tạo hồ sơ mới</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-2 py-1 space-y-1 custom-scrollbar">
        <p className="px-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">Hồ sơ gần đây</p>
        {sessions.map((s) => (
          <SessionListItem
            key={s.id}
            session={s}
            isActive={s.id === activeSessionId}
            onSelect={onSelectSession}
            onDelete={onDeleteSession}
            onRename={onRenameSession}
          />
        ))}

        {onLoadOlderSessions && (
          <button
            type="button"
            disabled={loadingHistory}
            onClick={onLoadOlderSessions}
            className="w-full text-center py-2 text-[11px] text-slate-500 hover:text-slate-300 transition-colors cursor-pointer"
          >
            {loadingHistory ? "Đang tải hồ sơ cũ..." : "Xem thêm hồ sơ cũ"}
          </button>
        )}
      </div>

      <div className="p-2 border-t border-slate-800 space-y-0.5 text-xs">
        <button
          type="button"
          onClick={onOpenDocuments}
          className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 cursor-pointer transition-colors"
        >
          <BookOpen className="w-4 h-4 text-blue-400" />
          <span>Thư viện pháp quy (RAG)</span>
        </button>

        <button
          type="button"
          onClick={onOpenInspectionLog}
          className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 cursor-pointer transition-colors"
        >
          <History className="w-4 h-4 text-emerald-400" />
          <span>Nhật ký kiểm tra</span>
        </button>

        <button
          type="button"
          onClick={onOpenUserManagement}
          className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-slate-400 hover:bg-slate-800 hover:text-slate-200 cursor-pointer transition-colors"
        >
          {currentUser.role === "admin" ? <Users className="w-4 h-4 text-amber-400" /> : <KeyRound className="w-4 h-4 text-amber-400" />}
          <span>{currentUser.role === "admin" ? "Quản lý tài khoản" : "Đổi mật khẩu"}</span>
        </button>

        <div className="pt-1.5 mt-1 border-t border-slate-800/80 flex items-center justify-between px-2.5 py-1">
          <div className="min-w-0 pr-2">
            <p className="text-xs font-bold text-white truncate">{currentUser.fullName || currentUser.username}</p>
            <p className="text-[10px] text-slate-500">{currentUser.role === "admin" ? "Quản trị viên" : "Nhân viên"}</p>
          </div>
          <button type="button" onClick={onLogout} className="p-1 text-slate-400 hover:text-red-400 rounded cursor-pointer" title="Đăng xuất">
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};
