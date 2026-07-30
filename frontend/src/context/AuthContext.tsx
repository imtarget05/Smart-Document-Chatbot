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

// Use relative path in development so Vite proxy handles requests.
// In production, set VITE_API_URL to the full backend URL.
const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "/api";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);

  const login = useCallback(
    (newToken: string, newUsername: string, newRole: string) => {
      setToken(newToken);
      setUsername(newUsername);
      setRole(newRole);
    },
    [],
  );

  const logout = useCallback(() => {
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