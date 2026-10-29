import React, { useState, useRef, useEffect } from "react";
import { Trash2, Pencil, Check, X } from "lucide-react";

interface SessionSummary {
  id: string;
  title: string;
  updatedAt: string;
}

interface SessionListItemProps {
  session: SessionSummary;
  isActive: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  onRename?: (id: string, newTitle: string) => void;
}

export const SessionListItem: React.FC<SessionListItemProps> = ({
  session,
  isActive,
  onSelect,
  onDelete,
  onRename,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(session.title || "");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isEditing) {
      setEditTitle(session.title || "");
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isEditing, session.title]);

  const handleSave = (e?: React.FormEvent) => {
    e?.preventDefault();
    e?.stopPropagation();
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== session.title) {
      onRename?.(session.id, trimmed);
    }
    setIsEditing(false);
  };

  const handleCancel = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsEditing(false);
    setEditTitle(session.title || "");
  };

  if (isEditing) {
    return (
      <form
        onSubmit={handleSave}
        onClick={(e) => e.stopPropagation()}
        className="flex items-center gap-1 px-2 py-1.5 rounded-xl bg-slate-800 text-xs border border-brand-orange"
      >
        <input
          ref={inputRef}
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") setIsEditing(false);
          }}
          className="flex-1 bg-transparent text-white font-medium outline-none text-xs px-1"
        />
        <button
          type="submit"
          className="p-1 text-emerald-400 hover:text-emerald-300 rounded cursor-pointer"
          title="Lưu tên mới"
        >
          <Check className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={handleCancel}
          className="p-1 text-slate-400 hover:text-slate-300 rounded cursor-pointer"
          title="Hủy"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </form>
    );
  }

  return (
    <div
      onClick={() => onSelect(session.id)}
      onDoubleClick={() => setIsEditing(true)}
      className={`group flex items-center justify-between px-2.5 py-2 rounded-xl text-xs cursor-pointer transition-colors ${
        isActive
          ? "bg-slate-800 text-white font-bold"
          : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
      }`}
    >
      <span className="truncate pr-2 select-none" title={session.title}>
        {session.title || "Hồ sơ chưa đặt tên"}
      </span>

      <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setIsEditing(true);
          }}
          className="p-1 hover:text-brand-orange text-slate-500 rounded transition-colors cursor-pointer"
          title="Đổi tên hồ sơ"
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(session.id);
          }}
          className="p-1 hover:text-red-400 text-slate-500 rounded transition-colors cursor-pointer"
          title="Xóa hồ sơ"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};

