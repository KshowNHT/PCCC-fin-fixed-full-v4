// Lớp API tập trung: gắn Authorization header (JWT) vào mọi request, quản lý
// vòng đời token (Silent Sliding Refresh), đồng bộ đa tab (visibilitychange /
// focus / storage) và thu hồi token trên server khi logout.

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  ""
).replace(/\/$/, "");
export const apiUrl = (path: string) =>
  `${API_BASE_URL}${path.startsWith("/") ? path : "/" + path}`;

const TOKEN_KEY = "pccc_token";
const USER_KEY = "pccc_user";

// Ngưỡng còn lại (giây) để chủ động xin cấp token mới (10 phút trước khi hết hạn)
const REFRESH_THRESHOLD_SECONDS = 600;
// Ân hạn tối đa sau khi vừa hết hạn (giây) khi người dùng chuyển từ tab khác quay lại (5 phút)
const REFRESH_GRACE_SECONDS = 300;
// Khoảng thời gian coi là người dùng đang hoạt động (30 phút kể từ tương tác cuối)
const ACTIVE_USER_WINDOW_MS = 30 * 60 * 1000;

export interface AuthUser {
  id: string;
  username: string;
  fullName: string;
  role: "admin" | "staff";
}

export interface JwtPayloadInfo {
  sub?: string;
  username?: string;
  role?: string;
  iat?: number;
  exp?: number;
  jti?: string;
  sid?: string;
  siat?: number;
}

let lastActivityTimestamp = Date.now();
let refreshPromise: Promise<string | null> | null = null;
let lifecycleInitialized = false;

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

/** Giải mã an toàn phần payload của JWT (trả về null nếu là chuỗi mock trong test). */
export function parseJwtPayload(token: string | null | undefined): JwtPayloadInfo | null {
  if (!token || typeof token !== "string") return null;
  const parts = token.split(".");
  if (parts.length !== 3) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    const json = atob(padded);
    const parsed = JSON.parse(json);
    if (!parsed || typeof parsed !== "object" || typeof parsed.exp !== "number") {
      return null;
    }
    return parsed as JwtPayloadInfo;
  } catch {
    return null;
  }
}

/**
 * Kiểm tra 2 token có thuộc CÙNG MỘT PHIÊN ĐĂNG NHẬP hay không.
 * - Khi hệ thống tự động cấp token mới (Silent Refresh), chuỗi JWT thay đổi nhưng
 *   `sub` (user ID) và `sid` (Session ID) giữ nguyên -> trả về `true` để không làm
 *   hủy các request/thao tác đang chạy của người dùng.
 * - Khi người dùng đăng xuất, đổi tài khoản, hoặc đăng nhập phiên mới (`sid` mới),
 *   hoặc trong unit test gán token giả khác -> trả về `false`.
 */
export function isSameAuthSession(
  tokenA: string | null | undefined,
  tokenB: string | null | undefined = getToken()
): boolean {
  if (!tokenA || !tokenB) return false;
  if (tokenA === tokenB) return true;
  const payloadA = parseJwtPayload(tokenA);
  const payloadB = parseJwtPayload(tokenB);
  if (payloadA && payloadB && payloadA.sub && payloadA.sid) {
    return payloadA.sub === payloadB.sub && payloadA.sid === payloadB.sid;
  }
  return false;
}

/** Kiểm tra xem JWT thật có đang nằm trong vùng cần gia hạn (hoặc vừa hết hạn trong ân hạn khi chuyển tab) không. */
export function shouldRefreshToken(token: string | null | undefined): boolean {
  const payload = parseJwtPayload(token);
  if (!payload || typeof payload.exp !== "number") return false;
  const nowSec = Math.floor(Date.now() / 1000);
  const remainingSec = payload.exp - nowSec;
  return remainingSec <= REFRESH_THRESHOLD_SECONDS && remainingSec >= -REFRESH_GRACE_SECONDS;
}

export function getStoredUser(): AuthUser | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    const user = JSON.parse(raw);
    return user && typeof user.id === "string" && ["admin", "staff"].includes(user.role)
      ? (user as AuthUser)
      : null;
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

/**
 * Xin cấp Access Token mới từ `/api/auth/refresh` (dùng khóa mutex `refreshPromise`
 * để tránh gọi trùng khi nhiều request hoặc nhiều sự kiện chuyển tab xảy ra cùng lúc).
 */
export async function refreshAccessToken(expectedToken?: string | null): Promise<string | null> {
  const currentStored = getToken();
  const baseToken = expectedToken || currentStored;
  if (!baseToken || !parseJwtPayload(baseToken)) return null;

  // Nếu một tab khác vừa gia hạn token mới vào localStorage cho cùng phiên này, dùng luôn!
  if (
    currentStored &&
    currentStored !== baseToken &&
    isSameAuthSession(baseToken, currentStored) &&
    !shouldRefreshToken(currentStored)
  ) {
    return currentStored;
  }

  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = (async () => {
    try {
      const res = await fetch(apiUrl("/api/auth/refresh"), {
        method: "POST",
        headers: {
          Authorization: `Bearer ${baseToken}`,
          "Content-Type": "application/json",
        },
        signal: AbortSignal.timeout(15_000),
      });
      if (!res.ok) return null;
      const data = await res.json();
      if (!data || typeof data.access_token !== "string") return null;

      // Chỉ cập nhật vào localStorage nếu phiên đăng nhập chưa bị người dùng chủ động đăng xuất/đổi sang phiên khác
      const latestStored = getToken();
      if (latestStored && isSameAuthSession(baseToken, latestStored)) {
        const currentUser = getStoredUser();
        const updatedUser: AuthUser = data.user
          ? {
              id: data.user.id,
              username: data.user.username,
              fullName: data.user.fullName ?? data.user.full_name ?? currentUser?.fullName ?? "",
              role: data.user.role,
            }
          : currentUser || { id: "", username: "", fullName: "", role: "staff" };
        setAuth(data.access_token, updatedUser);
      }
      return data.access_token;
    } catch {
      return null;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}

/**
 * Khởi tạo bộ theo dõi hoạt động người dùng & bảo vệ phiên khi chuyển tab trình duyệt.
 * - Tự động làm mới token ngầm khi người dùng đang hoạt động.
 * - Khi người dùng chuyển sang tab khác rồi quay lại (visibilitychange / focus),
 *   kiểm tra và gia hạn ngay token (kể cả khi timer của tab ẩn bị trình duyệt đóng băng).
 */
export function initAuthLifecycle(): void {
  if (lifecycleInitialized || typeof window === "undefined") return;
  lifecycleInitialized = true;

  const markActivity = () => {
    const now = Date.now();
    if (now - lastActivityTimestamp > 5_000) {
      lastActivityTimestamp = now;
    }
  };

  for (const evt of ["mousedown", "keydown", "touchstart", "scroll", "click"] as const) {
    window.addEventListener(evt, markActivity, { passive: true });
  }

  const checkAndRefreshOnResume = () => {
    lastActivityTimestamp = Date.now();
    const token = getToken();
    if (token && shouldRefreshToken(token)) {
      void refreshAccessToken(token);
    }
  };

  window.addEventListener("focus", checkAndRefreshOnResume);
  window.addEventListener("pageshow", checkAndRefreshOnResume);
  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") {
        checkAndRefreshOnResume();
      }
    });
  }

  // Đồng bộ giữa nhiều tab: chỉ đăng xuất nếu tab khác thực sự xoá token (logout)
  window.addEventListener("storage", (e: StorageEvent) => {
    if (e.key === TOKEN_KEY && e.oldValue && !e.newValue) {
      window.dispatchEvent(new CustomEvent("pccc:unauthorized"));
    }
  });

  // Kiểm tra định kỳ mỗi 60 giây cho người dùng đang làm việc
  const timer = setInterval(() => {
    const token = getToken();
    if (!token) return;
    const isRecentlyActive = Date.now() - lastActivityTimestamp <= ACTIVE_USER_WINDOW_MS;
    if (isRecentlyActive && shouldRefreshToken(token)) {
      void refreshAccessToken(token);
    }
  }, 60_000);
  if (typeof (timer as any)?.unref === "function") {
    (timer as any).unref();
  }
}

initAuthLifecycle();

/**
 * Wrapper fetch() tự động gắn Bearer token, tự động gia hạn ngầm (Silent Refresh)
 * khi người dùng đang hoạt động hoặc vừa chuyển từ tab khác quay lại, và chỉ đăng xuất
 * khi phiên thực sự hết hạn/bị thu hồi.
 */
export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  // Đọc token đồng bộ ngay dòng đầu tiên để bảo toàn thứ tự microtask cho các kiểm tra đồng bộ
  let token = getToken();

  const isAuthEndpoint =
    path.startsWith("/api/auth/login") ||
    path.startsWith("/api/auth/refresh") ||
    path.startsWith("/api/auth/logout");

  // Nếu JWT thật sắp hết hạn (hoặc vừa hết hạn trong ân hạn 5 phút khi chuyển tab), gia hạn trước khi gọi API
  if (token && !isAuthEndpoint && shouldRefreshToken(token)) {
    const refreshed = await refreshAccessToken(token);
    if (refreshed) {
      token = refreshed;
    }
  }

  const buildHeaders = (bearerToken: string | null) => {
    const h = new Headers(options.headers || {});
    if (bearerToken) h.set("Authorization", `Bearer ${bearerToken}`);
    if (options.body && !(options.body instanceof FormData) && !h.has("Content-Type")) {
      h.set("Content-Type", "application/json");
    }
    return h;
  };

  const timeout = AbortSignal.timeout(100_000);
  const signal = options.signal ? AbortSignal.any([options.signal, timeout]) : timeout;
  let res = await fetch(apiUrl(path), { ...options, headers: buildHeaders(token), signal });

  // Chặn phản hồi của phiên đăng nhập cũ ghi đè lên phiên đăng nhập mới
  // (vẫn cho phép trường hợp cùng phiên đăng nhập vừa được Silent Refresh).
  if (token !== getToken() && !isSameAuthSession(token, getToken())) {
    throw new DOMException("Phiên đăng nhập đã thay đổi.", "AbortError");
  }

  // Nếu gặp 401 trên JWT thật (ví dụ vừa quay lại từ tab khác đúng giây hết hạn),
  // thử đồng bộ từ localStorage hoặc gọi refresh 1 lần trước khi đăng xuất.
  if (res.status === 401 && token && !isAuthEndpoint && parseJwtPayload(token)) {
    const refreshedToken = await refreshAccessToken(token);
    if (refreshedToken && isSameAuthSession(token, getToken())) {
      token = refreshedToken;
      const retryTimeout = AbortSignal.timeout(100_000);
      const retrySignal = options.signal
        ? AbortSignal.any([options.signal, retryTimeout])
        : retryTimeout;
      res = await fetch(apiUrl(path), {
        ...options,
        headers: buildHeaders(token),
        signal: retrySignal,
      });
      if (token !== getToken() && !isSameAuthSession(token, getToken())) {
        throw new DOMException("Phiên đăng nhập đã thay đổi.", "AbortError");
      }
    }
  }

  if (res.status === 401) {
    clearAuth();
    window.dispatchEvent(new CustomEvent("pccc:unauthorized"));
  }

  // Kiểm tra phiên trong lúc đang đọc stream body
  for (const method of ["json", "blob", "text", "arrayBuffer"] as const) {
    const original = res[method].bind(res);
    (res as any)[method] = async () => {
      const body = await original();
      if (token !== getToken() && !isSameAuthSession(token, getToken())) {
        throw new DOMException("Phiên đăng nhập đã thay đổi.", "AbortError");
      }
      return body;
    };
  }

  return res;
}

export async function login(username: string, password: string): Promise<AuthUser> {
  const res = await fetch(apiUrl("/api/auth/login-json"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
    signal: AbortSignal.timeout(15_000),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      err.detail || "Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản/mật khẩu."
    );
  }

  const data = await res.json();
  lastActivityTimestamp = Date.now();
  setAuth(data.access_token, data.user);
  return data.user;
}

export function logout() {
  const token = getToken();
  clearAuth();
  if (token && parseJwtPayload(token)) {
    // Gửi yêu cầu thu hồi token lên server (không chặn luồng UI)
    void fetch(apiUrl("/api/auth/logout"), {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(5_000),
    }).catch(() => {});
  }
}

/** Xác thực token hiện có (nếu vừa reload trang hoặc quay lại tab) còn hợp lệ hay không. */
export async function verifySession(): Promise<AuthUser | null> {
  const token = getToken();
  if (!token) return null;
  try {
    const res = await apiFetch("/api/auth/me");
    if (!res.ok) return null;
    const me = await res.json();
    const latestToken = getToken() || token;
    const user: AuthUser = {
      id: me.id,
      username: me.username,
      fullName: me.full_name,
      role: me.role,
    };
    setAuth(latestToken, user);
    return user;
  } catch {
    return null;
  }
}
