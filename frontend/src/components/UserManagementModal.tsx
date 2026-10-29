import React, { useEffect, useState } from "react";
import {
  X,
  UserPlus,
  Users,
  Shield,
  Lock,
  Unlock,
  Trash2,
  KeyRound,
  Eye,
  EyeOff,
  Loader2,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import { apiFetch, AuthUser } from "../lib/api";

export interface ManagedUser {
  id: string;
  username: string;
  full_name: string;
  email?: string | null;
  role: "admin" | "staff";
  is_active: boolean;
  created_at: string;
}

interface UserManagementModalProps {
  currentUser: AuthUser;
  onClose: () => void;
  onPasswordChanged?: () => void;
}

const MAX_STAFF_LIMIT = 10;

export function UserManagementModal({
  currentUser,
  onClose,
  onPasswordChanged,
}: UserManagementModalProps) {
  const isAdmin = currentUser.role === "admin";
  const [activeTab, setActiveTab] = useState<"users" | "my-password">(
    isAdmin ? "users" : "my-password"
  );

  // Danh sách tài khoản (chỉ dành cho Admin)
  const [users, setUsers] = useState<ManagedUser[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Form tạo tài khoản mới
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"staff" | "admin">("staff");
  const [showCreatePwd, setShowCreatePwd] = useState(false);
  const [isCreating, setIsCreating] = useState(false);

  // Đặt lại mật khẩu cho nhân viên
  const [resetTargetId, setResetTargetId] = useState<string | null>(null);
  const [resetNewPassword, setResetNewPassword] = useState("");
  const [showResetPwd, setShowResetPwd] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState<string | null>(null);

  // Form tự đổi mật khẩu cá nhân
  const [oldPassword, setOldPassword] = useState("");
  const [myNewPassword, setMyNewPassword] = useState("");
  const [showMyPwd, setShowMyPwd] = useState(false);
  const [isChangingMyPwd, setIsChangingMyPwd] = useState(false);

  const staffCount = users.filter((u) => u.role === "staff").length;
  const isStaffQuotaReached = staffCount >= MAX_STAFF_LIMIT && role === "staff";

  const fetchUsers = async () => {
    if (!isAdmin) return;
    setIsLoading(true);
    setError("");
    try {
      const res = await apiFetch("/api/auth/users");
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Không tải được danh sách tài khoản.");
      }
      const data = await res.json();
      setUsers(Array.isArray(data) ? data : []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Lỗi kết nối máy chủ.";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAdmin && activeTab === "users") {
      fetchUsers();
    }
  }, [isAdmin, activeTab]);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    if (isStaffQuotaReached) {
      setError(`Hệ thống chỉ cho phép tạo tối đa ${MAX_STAFF_LIMIT} tài khoản nhân viên.`);
      return;
    }

    setIsCreating(true);
    try {
      const res = await apiFetch("/api/auth/users", {
        method: "POST",
        body: JSON.stringify({
          username: username.trim(),
          full_name: fullName.trim(),
          email: email.trim() || null,
          password,
          role,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg || "").join("; ")
          : data.detail;
        throw new Error(detail || "Không thể tạo tài khoản.");
      }
      setSuccessMsg(`Đã tạo tài khoản "${data.username}" thành công!`);
      setUsername("");
      setFullName("");
      setEmail("");
      setPassword("");
      setRole("staff");
      await fetchUsers();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Không thể tạo tài khoản.";
      setError(msg);
    } finally {
      setIsCreating(false);
    }
  };

  const handleToggleActive = async (u: ManagedUser) => {
    setError("");
    setSuccessMsg("");
    setIsActionLoading(u.id);
    try {
      const res = await apiFetch(`/api/auth/users/${u.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_active: !u.is_active }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Không thể cập nhật trạng thái tài khoản.");
      setSuccessMsg(
        `Đã ${data.is_active ? "mở khoá" : "khoá"} tài khoản "${u.username}".`
      );
      await fetchUsers();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Lỗi cập nhật tài khoản.";
      setError(msg);
    } finally {
      setIsActionLoading(null);
    }
  };

  const handleResetPassword = async (userId: string, targetUsername: string) => {
    if (!resetNewPassword) return;
    setError("");
    setSuccessMsg("");
    setIsActionLoading(userId);
    try {
      const res = await apiFetch(`/api/auth/users/${userId}`, {
        method: "PUT",
        body: JSON.stringify({ new_password: resetNewPassword }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg || "").join("; ")
          : data.detail;
        throw new Error(detail || "Không thể đặt lại mật khẩu.");
      }
      setSuccessMsg(`Đã cấp mật khẩu mới cho tài khoản "${targetUsername}".`);
      setResetTargetId(null);
      setResetNewPassword("");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Không thể đặt lại mật khẩu.";
      setError(msg);
    } finally {
      setIsActionLoading(null);
    }
  };

  const handleDeleteUser = async (u: ManagedUser) => {
    if (
      !window.confirm(
        `Bạn có chắc chắn muốn XOÁ tài khoản "${u.username}" (${u.full_name || "Chưa đặt tên"})?\nToàn bộ hồ sơ gắn với tài khoản này cũng sẽ bị xoá.`
      )
    ) {
      return;
    }
    setError("");
    setSuccessMsg("");
    setIsActionLoading(u.id);
    try {
      const res = await apiFetch(`/api/auth/users/${u.id}`, {
        method: "DELETE",
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || "Không thể xoá tài khoản.");
      setSuccessMsg(`Đã xoá tài khoản "${u.username}".`);
      await fetchUsers();
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Lỗi khi xoá tài khoản.";
      setError(msg);
    } finally {
      setIsActionLoading(null);
    }
  };

  const handleChangeMyPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setIsChangingMyPwd(true);
    try {
      const res = await apiFetch("/api/auth/me/password", {
        method: "PUT",
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: myNewPassword,
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail.map((d: { msg?: string }) => d.msg || "").join("; ")
          : data.detail;
        throw new Error(detail || "Không thể đổi mật khẩu.");
      }
      setSuccessMsg("Đã đổi mật khẩu thành công! Vui lòng đăng nhập lại bằng mật khẩu mới.");
      setOldPassword("");
      setMyNewPassword("");
      if (onPasswordChanged) {
        setTimeout(() => onPasswordChanged(), 1200);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Không thể đổi mật khẩu.";
      setError(msg);
    } finally {
      setIsChangingMyPwd(false);
    }
  };

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString("vi-VN");
    } catch {
      return iso;
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-3xl max-h-[88vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-200 shrink-0">
          <div className="flex items-center gap-2.5">
            <Users className="w-5 h-5 text-blue-600" />
            <h3 className="font-semibold text-slate-800 text-base">
              {isAdmin ? "Quản lý tài khoản hệ thống" : "Tài khoản cá nhân"}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded hover:bg-slate-100 text-slate-500"
            title="Đóng"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        {isAdmin && (
          <div className="flex gap-2 px-5 pt-3 border-b border-slate-100 pb-3 shrink-0">
            <button
              type="button"
              onClick={() => {
                setActiveTab("users");
                setError("");
                setSuccessMsg("");
              }}
              className={`text-xs px-3.5 py-1.5 rounded-full transition-colors flex items-center gap-1.5 ${
                activeTab === "users"
                  ? "bg-blue-600 text-white font-medium"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Danh sách & Cấp tài khoản ({staffCount}/{MAX_STAFF_LIMIT})
            </button>
            <button
              type="button"
              onClick={() => {
                setActiveTab("my-password");
                setError("");
                setSuccessMsg("");
              }}
              className={`text-xs px-3.5 py-1.5 rounded-full transition-colors flex items-center gap-1.5 ${
                activeTab === "my-password"
                  ? "bg-blue-600 text-white font-medium"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <KeyRound className="w-3.5 h-3.5" />
              Đổi mật khẩu của tôi
            </button>
          </div>
        )}

        {/* Thông báo lỗi / thành công */}
        {error && (
          <div
            role="alert"
            className="mx-5 mt-3 px-3.5 py-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2 shrink-0"
          >
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="flex-1">{error}</span>
          </div>
        )}
        {successMsg && (
          <div
            role="status"
            className="mx-5 mt-3 px-3.5 py-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs flex items-center gap-2 shrink-0"
          >
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span className="flex-1">{successMsg}</span>
          </div>
        )}

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          {activeTab === "users" && isAdmin ? (
            <>
              {/* Thanh hạn mức 10 tài khoản nhân viên */}
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3.5">
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="font-medium text-slate-700">
                    Hạn mức tài khoản Nhân viên (không tính Admin)
                  </span>
                  <span
                    className={`font-bold ${
                      staffCount >= MAX_STAFF_LIMIT
                        ? "text-red-600"
                        : staffCount >= 8
                        ? "text-amber-600"
                        : "text-blue-600"
                    }`}
                  >
                    Đã tạo: {staffCount} / {MAX_STAFF_LIMIT} tài khoản
                  </span>
                </div>
                <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full transition-all ${
                      staffCount >= MAX_STAFF_LIMIT
                        ? "bg-red-500"
                        : staffCount >= 8
                        ? "bg-amber-500"
                        : "bg-blue-600"
                    }`}
                    style={{
                      width: `${Math.min(100, (staffCount / MAX_STAFF_LIMIT) * 100)}%`,
                    }}
                  />
                </div>
                {staffCount >= MAX_STAFF_LIMIT && (
                  <p className="mt-1.5 text-xs text-red-600">
                    Đã đạt giới hạn tối đa {MAX_STAFF_LIMIT} tài khoản nhân viên. Nếu muốn cấp tài khoản nhân viên mới, vui lòng xoá bớt tài khoản nhân viên không còn sử dụng bên dưới.
                  </p>
                )}
              </div>

              {/* Form tạo tài khoản mới */}
              <form
                onSubmit={handleCreateUser}
                className="bg-white border border-slate-200 rounded-lg p-4 space-y-3"
              >
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                  <UserPlus className="w-4 h-4 text-blue-600" />
                  <span>Tạo tài khoản mới</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Tên đăng nhập <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="VD: ky_su_01"
                      pattern="^[a-zA-Z0-9_.-]+$"
                      minLength={3}
                      maxLength={64}
                      required
                      className="w-full text-sm border border-slate-300 rounded-md px-3 py-1.5 outline-none focus:border-blue-500"
                    />
                    <span className="text-[11px] text-slate-400">
                      3–64 ký tự, chỉ gồm chữ không dấu, số, dấu chấm, gạch dưới/ngang.
                    </span>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Họ và tên hiển thị
                    </label>
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="VD: Nguyễn Văn A"
                      maxLength={255}
                      className="w-full text-sm border border-slate-300 rounded-md px-3 py-1.5 outline-none focus:border-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Mật khẩu khởi tạo <span className="text-red-500">*</span>
                    </label>
                    <div className="relative">
                      <input
                        type={showCreatePwd ? "text" : "password"}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="Tối thiểu 10 ký tự (chữ + số)"
                        minLength={10}
                        maxLength={128}
                        required
                        className="w-full text-sm border border-slate-300 rounded-md pl-3 pr-9 py-1.5 outline-none focus:border-blue-500"
                      />
                      <button
                        type="button"
                        onClick={() => setShowCreatePwd((v) => !v)}
                        className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600"
                        tabIndex={-1}
                      >
                        {showCreatePwd ? (
                          <EyeOff className="w-4 h-4" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    <span className="text-[11px] text-slate-400">
                      Bắt buộc ít nhất 10 ký tự, có cả chữ cái và chữ số.
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Email (tuỳ chọn)
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="nv@congty.vn"
                        maxLength={255}
                        className="w-full text-sm border border-slate-300 rounded-md px-2.5 py-1.5 outline-none focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-slate-700 mb-1">
                        Vai trò
                      </label>
                      <select
                        value={role}
                        onChange={(e) =>
                          setRole(e.target.value as "staff" | "admin")
                        }
                        className="w-full text-sm border border-slate-300 rounded-md px-2.5 py-1.5 outline-none focus:border-blue-500 bg-white"
                      >
                        <option value="staff">Nhân viên (Staff)</option>
                        <option value="admin">Quản trị (Admin)</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div className="flex justify-end pt-1">
                  <button
                    type="submit"
                    disabled={isCreating || isStaffQuotaReached}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-md text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 transition-colors"
                  >
                    {isCreating ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <UserPlus className="w-3.5 h-3.5" />
                    )}
                    {isStaffQuotaReached
                      ? `Đã đủ ${MAX_STAFF_LIMIT}/${MAX_STAFF_LIMIT} nhân viên`
                      : "Tạo tài khoản"}
                  </button>
                </div>
              </form>

              {/* Bảng danh sách tài khoản */}
              <div>
                <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                  Danh sách tài khoản hiện có ({users.length})
                </h4>
                {isLoading ? (
                  <div className="text-center text-sm text-slate-400 py-6">
                    Đang tải danh sách tài khoản...
                  </div>
                ) : (
                  <div className="border border-slate-200 rounded-lg overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-slate-50 text-xs text-slate-500 border-b border-slate-200">
                        <tr>
                          <th className="text-left py-2.5 px-3 font-medium">
                            Tài khoản
                          </th>
                          <th className="text-left py-2.5 px-3 font-medium">
                            Họ tên / Email
                          </th>
                          <th className="text-left py-2.5 px-3 font-medium">
                            Vai trò
                          </th>
                          <th className="text-left py-2.5 px-3 font-medium">
                            Trạng thái
                          </th>
                          <th className="text-right py-2.5 px-3 font-medium">
                            Thao tác
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {users.map((u) => {
                          const isSelf = u.id === currentUser.id;
                          return (
                            <React.Fragment key={u.id}>
                              <tr className="hover:bg-slate-50/70">
                                <td className="py-2.5 px-3 font-medium text-slate-800">
                                  {u.username}
                                  {isSelf && (
                                    <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-600 font-normal">
                                      Bạn
                                    </span>
                                  )}
                                  <div className="text-[11px] text-slate-400 font-normal">
                                    Tạo: {formatDate(u.created_at)}
                                  </div>
                                </td>
                                <td className="py-2.5 px-3 text-slate-600 text-xs">
                                  <div>{u.full_name || "—"}</div>
                                  {u.email && (
                                    <div className="text-slate-400">{u.email}</div>
                                  )}
                                </td>
                                <td className="py-2.5 px-3">
                                  {u.role === "admin" ? (
                                    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-700 font-medium">
                                      <Shield className="w-3 h-3" /> Quản trị
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                                      Nhân viên
                                    </span>
                                  )}
                                </td>
                                <td className="py-2.5 px-3">
                                  {u.is_active ? (
                                    <span className="inline-flex items-center text-xs text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                                      Hoạt động
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center text-xs text-red-700 bg-red-50 px-2 py-0.5 rounded-full">
                                      Đã khoá
                                    </span>
                                  )}
                                </td>
                                <td className="py-2.5 px-3 text-right whitespace-nowrap">
                                  <div className="inline-flex items-center gap-1">
                                    <button
                                      type="button"
                                      onClick={() => {
                                        setResetTargetId(
                                          resetTargetId === u.id ? null : u.id
                                        );
                                        setResetNewPassword("");
                                      }}
                                      className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                                      title="Cấp lại mật khẩu"
                                    >
                                      <KeyRound className="w-3.5 h-3.5" />
                                    </button>
                                    {!isSelf && (
                                      <>
                                        <button
                                          type="button"
                                          disabled={isActionLoading === u.id}
                                          onClick={() => handleToggleActive(u)}
                                          className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                                          title={
                                            u.is_active
                                              ? "Khoá tài khoản"
                                              : "Mở khoá tài khoản"
                                          }
                                        >
                                          {u.is_active ? (
                                            <Lock className="w-3.5 h-3.5 text-amber-600" />
                                          ) : (
                                            <Unlock className="w-3.5 h-3.5 text-emerald-600" />
                                          )}
                                        </button>
                                        <button
                                          type="button"
                                          disabled={isActionLoading === u.id}
                                          onClick={() => handleDeleteUser(u)}
                                          className="p-1.5 rounded hover:bg-red-50 text-red-600"
                                          title="Xoá tài khoản"
                                        >
                                          <Trash2 className="w-3.5 h-3.5" />
                                        </button>
                                      </>
                                    )}
                                  </div>
                                </td>
                              </tr>
                              {resetTargetId === u.id && (
                                <tr className="bg-blue-50/50">
                                  <td colSpan={5} className="px-3 py-2.5">
                                    <div className="flex flex-wrap items-center gap-2 justify-end">
                                      <span className="text-xs text-slate-700 font-medium">
                                        Đặt mật khẩu mới cho{" "}
                                        <strong>{u.username}</strong>:
                                      </span>
                                      <div className="relative">
                                        <input
                                          type={showResetPwd ? "text" : "password"}
                                          value={resetNewPassword}
                                          onChange={(e) =>
                                            setResetNewPassword(e.target.value)
                                          }
                                          placeholder="Tối thiểu 10 ký tự (chữ + số)"
                                          className="text-xs border border-slate-300 rounded px-2.5 py-1 pr-7 bg-white outline-none focus:border-blue-500 w-56"
                                        />
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setShowResetPwd((v) => !v)
                                          }
                                          className="absolute inset-y-0 right-0 pr-2 flex items-center text-slate-400"
                                        >
                                          {showResetPwd ? (
                                            <EyeOff className="w-3.5 h-3.5" />
                                          ) : (
                                            <Eye className="w-3.5 h-3.5" />
                                          )}
                                        </button>
                                      </div>
                                      <button
                                        type="button"
                                        disabled={
                                          isActionLoading === u.id ||
                                          resetNewPassword.length < 10
                                        }
                                        onClick={() =>
                                          handleResetPassword(u.id, u.username)
                                        }
                                        className="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                                      >
                                        Lưu mật khẩu
                                      </button>
                                      <button
                                        type="button"
                                        onClick={() => setResetTargetId(null)}
                                        className="text-xs px-2.5 py-1 rounded bg-white border border-slate-300 text-slate-600 hover:bg-slate-50"
                                      >
                                        Huỷ
                                      </button>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </>
          ) : (
            /* Tab đổi mật khẩu cá nhân */
            <form
              onSubmit={handleChangeMyPassword}
              className="max-w-md mx-auto bg-white border border-slate-200 rounded-lg p-5 space-y-4"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
                <KeyRound className="w-4 h-4 text-blue-600" />
                <span>Đổi mật khẩu tài khoản ({currentUser.username})</span>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Mật khẩu hiện tại <span className="text-red-500">*</span>
                </label>
                <input
                  type={showMyPwd ? "text" : "password"}
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  className="w-full text-sm border border-slate-300 rounded-md px-3 py-1.5 outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Mật khẩu mới <span className="text-red-500">*</span>
                </label>
                <div className="relative">
                  <input
                    type={showMyPwd ? "text" : "password"}
                    value={myNewPassword}
                    onChange={(e) => setMyNewPassword(e.target.value)}
                    placeholder="Tối thiểu 10 ký tự (cả chữ và số)"
                    minLength={10}
                    maxLength={128}
                    required
                    className="w-full text-sm border border-slate-300 rounded-md pl-3 pr-9 py-1.5 outline-none focus:border-blue-500"
                  />
                  <button
                    type="button"
                    onClick={() => setShowMyPwd((v) => !v)}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600"
                  >
                    {showMyPwd ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <span className="text-[11px] text-slate-400">
                  Sau khi đổi mật khẩu, phiên đăng nhập hiện tại sẽ tự đăng xuất để bảo mật.
                </span>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="submit"
                  disabled={isChangingMyPwd}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-xs font-medium text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {isChangingMyPwd && (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  )}
                  Cập nhật mật khẩu
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}

