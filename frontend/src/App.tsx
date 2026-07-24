import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import ClassicChatPage from "./pages/ClassicChatPage";
import AgentChatPage from "./pages/AgentChatPage";
import DashboardPage from "./components/DashboardPage";
import KnowledgeBasePage from "./components/KnowledgeBasePage";
import DataSourcesPage from "./components/DataSourcesPage";
import EightDCasesPage from "./components/EightDCasesPage";
import EvaluationLabPage from "./components/EvaluationLabPage";
import AuditLogsPage from "./components/AuditLogsPage";
import SettingsPage from "./components/SettingsPage";
import AdminUsersPage from "./components/AdminUsersPage";
import ErrorBoundary from "./components/ErrorBoundary";
import "./App.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: 1,
    },
  },
});

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function RoleRoute({
  roles,
  children,
}: {
  roles: string[];
  children: React.ReactNode;
}) {
  const { isAdmin, isEngineer, isAuthenticated } = useAuth();
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  const hasRole = roles.some((r) => {
    if (r === "ADMIN") return isAdmin;
    if (r === "ENGINEER") return isEngineer || isAdmin;
    return true;
  });

  if (!hasRole) return <Navigate to="/classic" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { isAuthenticated, token } = useAuth();

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated ? <Navigate to="/classic" replace /> : <LoginPage />
        }
      />

      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/classic" replace />} />
        <Route
          path="/classic"
          element={
            <ErrorBoundary>
              <ClassicChatPage />
            </ErrorBoundary>
          }
        />
        <Route
          path="/agent"
          element={
            <ErrorBoundary>
              <AgentChatPage />
            </ErrorBoundary>
          }
        />
        <Route
          path="/dashboard"
          element={
            <ErrorBoundary>
              <DashboardPage />
            </ErrorBoundary>
          }
        />
        <Route
          path="/knowledge"
          element={
            <ErrorBoundary>
              <KnowledgeBasePage />
            </ErrorBoundary>
          }
        />
        <Route
          path="/datasources"
          element={
            <ErrorBoundary>
              {token ? (
                <DataSourcesPage token={token} />
              ) : (
                <div>Loading...</div>
              )}
            </ErrorBoundary>
          }
        />
        <Route
          path="/eightd"
          element={
            <RoleRoute roles={["ENGINEER", "ADMIN"]}>
              <ErrorBoundary>
                {token ? (
                  <EightDCasesPage token={token} />
                ) : (
                  <div>Loading...</div>
                )}
              </ErrorBoundary>
            </RoleRoute>
          }
        />
        <Route
          path="/evaluation"
          element={
            <RoleRoute roles={["ENGINEER", "ADMIN"]}>
              <ErrorBoundary>
                {token ? (
                  <EvaluationLabPage token={token} />
                ) : (
                  <div>Loading...</div>
                )}
              </ErrorBoundary>
            </RoleRoute>
          }
        />
        <Route
          path="/audit"
          element={
            <RoleRoute roles={["ADMIN"]}>
              <ErrorBoundary>
                {token ? (
                  <AuditLogsPage token={token} />
                ) : (
                  <div>Loading...</div>
                )}
              </ErrorBoundary>
            </RoleRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ErrorBoundary>
              <SettingsPage />
            </ErrorBoundary>
          }
        />
        <Route
          path="/admin"
          element={
            <RoleRoute roles={["ADMIN"]}>
              <ErrorBoundary>
                {token ? (
                  <AdminUsersPage token={token} />
                ) : (
                  <div>Loading...</div>
                )}
              </ErrorBoundary>
            </RoleRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  );
}
