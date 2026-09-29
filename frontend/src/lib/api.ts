// Lớp API tập trung: gắn Authorization header (JWT) vào mọi request, quản lý
// token trong localStorage, và các hàm login/logout — thay thế cơ chế
// isAuthenticated giả (client-side admin/admin) trước đây bằng auth thật
// gọi vào backend FastAPI (Ngày 1 kế hoạch: 'Viết API Authentication + JWT').

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");
export const apiUrl = (path: string) => `${API_BASE_URL}${path.startsWith("/") ? path : "/" + path}`;

const TOKEN_KEY = "pccc_token";
const USER_KEY = "pccc_user";

export interface AuthUser {
  id: string;
  username: string;
  fullName: string;
  role: "admin" | "staff";
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthUser;
  } catch {
    return null;
  }
}

function setAuth(token: string, user: AuthUser) {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

/** Wrapper fetch() tự động gắn Bearer token; tự đăng xuất nếu token hết hạn (401). */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(apiUrl(path), { ...options, headers });

  if (res.status === 401) {
    clearAuth();
    window.dispatchEvent(new CustomEvent("pccc:unauthorized"));
  }

  return res;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(apiUrl("/api/auth/login-json"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản/mật khẩu.");
  }

  const data = await res.json();
  setAuth(data.access_token, data.user);
  return data.user;
}

export function logout() {
  clearAuth();
}

/** Xác thực token hiện có (nếu vừa reload trang) còn hợp lệ hay không. */
export async function verifySession(): Promise<AuthUser | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await apiFetch("/api/auth/me");
    if (!res.ok) return null;
    const me = await res.json();
    const user: AuthUser = { id: me.id, username: me.username, fullName: me.full_name, role: me.role };
    setAuth(token, user);
    return user;
  } catch {
    return null;
  }
}
