import { useState, useEffect, useCallback } from "react";
import { AuthUser, getStoredUser, verifySession, logout } from "../lib/api";
import { activateCodeProtection } from "../lib/codeProtection";

export function useAppAuth() {
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(getStoredUser());
  const [authChecked, setAuthChecked] = useState(false);
  const [isDevToolsOpen, setIsDevToolsOpen] = useState(false);

  useEffect(() => {
    (async () => {
      const user = await verifySession();
      setCurrentUser(user);
      setAuthChecked(true);
    })();

    const handleUnauthorized = () => {
      logout();
      setCurrentUser(null);
    };

    window.addEventListener("pccc:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("pccc:unauthorized", handleUnauthorized);
  }, []);

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

  const handleLogout = useCallback(() => {
    logout();
    setCurrentUser(null);
  }, []);

  return {
    currentUser,
    setCurrentUser,
    authChecked,
    isDevToolsOpen,
    handleLogout,
  };
}

