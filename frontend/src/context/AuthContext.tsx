/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";

interface AuthContextType {
  token: string | null;
  username: string | null;
  role: string | null;
  login: (token: string, username: string, role: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
  isAdmin: boolean;
  isEngineer: boolean;
  isViewer: boolean;
  isInitializing: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

const STORAGE_KEY = "smartdoc.auth";

interface PersistedAuth {
  token: string;
  username: string;
  role: string;
}

function readPersistedAuth(): PersistedAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedAuth;
    if (parsed.token && parsed.username && parsed.role) return parsed;
    return null;
  } catch {
    return null;
  }
}

function writePersistedAuth(auth: PersistedAuth) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(auth));
}

function clearPersistedAuth() {
  localStorage.removeItem(STORAGE_KEY);
}

async function validateToken(token: string): Promise<boolean> {
  try {
    const res = await fetch("/api/documents", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [isInitializing, setIsInitializing] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const persisted = readPersistedAuth();
      if (!persisted) {
        setIsInitializing(false);
        return;
      }
      const valid = await validateToken(persisted.token);
      if (cancelled) return;
      if (valid) {
        setToken(persisted.token);
        setUsername(persisted.username);
        setRole(persisted.role);
      } else {
        clearPersistedAuth();
      }
      setIsInitializing(false);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(
    (newToken: string, newUsername: string, newRole: string) => {
      setToken(newToken);
      setUsername(newUsername);
      setRole(newRole);
      writePersistedAuth({ token: newToken, username: newUsername, role: newRole });
    },
    [],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUsername(null);
    setRole(null);
    clearPersistedAuth();
  }, []);

  const isAuthenticated = !!token;
  const isAdmin = role === "ROLE_ADMIN" || role === "ADMIN";
  const isEngineer = role === "ROLE_ENGINEER" || role === "ENGINEER";
  const isViewer = role === "ROLE_VIEWER" || role === "VIEWER";

  return (
    <AuthContext.Provider
      value={{
        token,
        username,
        role,
        login,
        logout,
        isAuthenticated,
        isAdmin,
        isEngineer,
        isViewer,
        isInitializing,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
