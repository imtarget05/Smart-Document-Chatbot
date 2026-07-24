import {
  createContext,
  useContext,
  useState,
  useCallback,
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
}

const AuthContext = createContext<AuthContextType | null>(null);

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "http://localhost:8080/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Note: JWT is now stored in httpOnly cookie (set by backend).
  // We keep username/role in memory only – NOT localStorage – to mitigate XSS.
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  const login = useCallback(
    (newToken: string, newUsername: string, newRole: string) => {
      // Do NOT store JWT in localStorage – backend sets httpOnly cookie.
      // Only keep non-sensitive identity info in memory for UI rendering.
      setToken(newToken);
      setUsername(newUsername);
      setRole(newRole);
    },
    [],
  );

  const logout = useCallback(() => {
    // Clear in-memory state. httpOnly cookie is cleared by backend /auth/logout.
    setToken(null);
    setUsername(null);
    setRole(null);
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

export { API_BASE_URL };
