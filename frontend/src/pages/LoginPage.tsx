import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../context/apiConfig";
import { csrfHeaders } from "../csrf";

export default function LoginPage() {
  const { login } = useAuth();
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authUsername, setAuthUsername] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showReset, setShowReset] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [resetSent, setResetSent] = useState(false);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authUsername.trim() || !authPassword.trim()) {
      setAuthError("Please fill in all fields");
      return;
    }
    if (authMode === "register" && authPassword !== confirmPassword) {
      setAuthError("Passwords do not match");
      return;
    }
    setAuthError("");
    setAuthLoading(true);

    try {
      const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify({
          username: authUsername,
          password: authPassword,
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || "Authentication failed");
      }

      const data = await response.json();
      login(data.token, data.username, data.role);

      setAuthUsername("");
      setAuthPassword("");
      setConfirmPassword("");
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = `${API_BASE_URL}/oauth2/authorization/google`;
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetEmail.trim()) {
      setAuthError("Please enter your email");
      return;
    }
    setAuthLoading(true);
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...csrfHeaders() },
        body: JSON.stringify({ email: resetEmail }),
      });
      if (!res.ok) throw new Error(await res.text() || "Failed to send reset email");
      setResetSent(true);
    } catch (err: unknown) {
      setAuthError(err instanceof Error ? err.message : "Reset failed");
    } finally {
      setAuthLoading(false);
    }
  };

  if (showReset) {
    return (
      <div className="min-h-screen bg-[#f8f9fa] flex items-center justify-center p-4 font-['Google_Sans','Roboto',sans-serif]">
        <div className="w-full max-w-[448px] bg-white border border-[#dadce0] rounded-[8px] p-10 pt-12">
          <div className="flex justify-center mb-4">
            <svg width="48" height="48" viewBox="0 0 48 48"><path fill="#4285F4" d="M24 24v8h12c-1 4-4 7-12 7-7 0-12-5-12-12s5-12 12-12c3 0 5 1 7 3l3-3C31 11 28 9 24 9 14 9 6 17 6 24s8 15 18 15c10 0 16-7 16-15 0-1 0-2 0-3H24z"/></svg>
          </div>
          <h1 className="text-[24px] text-[#202124] font-normal text-center">Reset password</h1>
          <p className="text-[16px] text-[#202124] text-center mt-2">Enter your email to receive reset instructions</p>
          <form onSubmit={handleReset} className="mt-8 space-y-6">
            <div className="relative">
              <input
                type="email"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                placeholder="Email"
                className="peer w-full px-4 py-3.5 border border-[#dadce0] rounded-[4px] text-[16px] text-[#202124] placeholder-transparent focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
              />
              <label className="absolute left-3 -top-2.5 bg-white px-1 text-[12px] text-[#5f6368] peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-[16px] peer-placeholder-shown:text-[#80868b] peer-focus:-top-2.5 peer-focus:text-[12px] peer-focus:text-[#1a73e8] transition-all">
                Email
              </label>
            </div>
            {resetSent && <p className="text-[#137333] text-[14px] bg-[#e6f4ea] border border-[#ceead6] px-4 py-3 rounded-[4px]">Reset link sent. Check your email.</p>}
            {authError && <p className="text-[#d93025] text-[14px]">{authError}</p>}
            <div className="flex justify-between items-center pt-2">
              <button type="button" onClick={() => setShowReset(false)} className="text-[#1a73e8] text-[14px] font-medium hover:bg-[#f8f9ff] px-2 py-1 rounded">Back to sign in</button>
              <button type="submit" disabled={authLoading} className="bg-[#1a73e8] hover:bg-[#185abc] text-white text-[14px] font-medium px-6 py-2.5 rounded-[4px] disabled:opacity-50 min-w-[80px]">
                {authLoading ? <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin inline-block"></span> : "Next"}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa] flex items-center justify-center p-4 font-['Google_Sans','Roboto',sans-serif]">
      <div className="w-full max-w-[448px] bg-white border border-[#dadce0] rounded-[8px] p-10 pt-12">
        <div className="flex justify-center mb-2">
          <svg width="75" height="24" viewBox="0 0 74 24"><path fill="#4285F4" d="M9.5 8.5c1.5 0 2.8.5 3.8 1.5l2.8-2.8C14.8 5.8 12.5 5 9.5 5 4.3 5 0 8.8 0 14s4.3 9 9.5 9c5.5 0 9.1-3.9 9.1-9 0-.6 0-1.2-.1-1.7H9.5V8.5z"/><path fill="#34A853" d="M35.5 12c0-.7-.1-1.4-.2-2H26v4h5.3c-.2 1.1-.9 2-1.9 2.6v3.4h3.1c1.8-1.7 2.8-4.1 2.8-6.9z"/><path fill="#FBBC05" d="M44 14c0-1.6-.3-3-.8-4.3L38 13l2.9 2.3c.5-1.4.8-2.9.8-4.5z"/><path fill="#EA4335" d="M52 8l-3 2.4 3 3.6c.5-1.5.8-3 .8-4.6 0-1.6-.3-3.1-.8-4.5z"/></svg>
        </div>
        <h1 className="text-[24px] leading-[32px] text-[#202124] font-normal text-center">
          {authMode === "login" ? "Sign in" : "Create account"}
        </h1>
        <p className="text-[16px] text-[#202124] text-center mt-1">to continue to Smart Doc</p>

        <form onSubmit={handleAuthSubmit} className="mt-8 space-y-5">
          <div className="relative">
            <input
              type="text"
              value={authUsername}
              onChange={(e) => setAuthUsername(e.target.value)}
              placeholder="Username or email"
              className="peer w-full px-3.5 py-3.5 border border-[#dadce0] rounded-[4px] text-[16px] text-[#202124] placeholder-transparent focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
            />
            <label className="absolute left-3 -top-2.5 bg-white px-1 text-[12px] text-[#5f6368] peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-[16px] peer-placeholder-shown:text-[#5f6368] peer-focus:-top-2.5 peer-focus:text-[12px] peer-focus:text-[#1a73e8] transition-all">
              Email or username
            </label>
          </div>

          <div className="relative">
            <input
              type="password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              placeholder="Password"
              className="peer w-full px-3.5 py-3.5 border border-[#dadce0] rounded-[4px] text-[16px] text-[#202124] placeholder-transparent focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
            />
            <label className="absolute left-3 -top-2.5 bg-white px-1 text-[12px] text-[#5f6368] peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-[16px] peer-placeholder-shown:text-[#5f6368] peer-focus:-top-2.5 peer-focus:text-[12px] peer-focus:text-[#1a73e8] transition-all">
              Password
            </label>
          </div>

          {authMode === "register" && (
            <div className="relative">
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                className="peer w-full px-3.5 py-3.5 border border-[#dadce0] rounded-[4px] text-[16px] text-[#202124] placeholder-transparent focus:outline-none focus:border-[#1a73e8] focus:ring-1 focus:ring-[#1a73e8]"
              />
              <label className="absolute left-3 -top-2.5 bg-white px-1 text-[12px] text-[#5f6368] peer-placeholder-shown:top-3.5 peer-placeholder-shown:text-[16px] peer-placeholder-shown:text-[#5f6368] peer-focus:-top-2.5 peer-focus:text-[12px] peer-focus:text-[#1a73e8] transition-all">
                Confirm password
              </label>
            </div>
          )}

          {authMode === "login" && (
            <div className="text-left -mt-2">
              <button type="button" onClick={() => setShowReset(true)} className="text-[#1a73e8] text-[14px] font-medium hover:underline">Forgot password?</button>
            </div>
          )}

          {authError && (
            <div className="flex items-start gap-2 text-[#d93025] text-[14px]">
              <svg className="w-5 h-5 mt-0.5 flex-shrink-0" fill="#d93025" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
              <span>{authError}</span>
            </div>
          )}

          <div className="flex justify-between items-center pt-2">
            <button
              type="button"
              onClick={() => {
                setAuthMode(authMode === "login" ? "register" : "login");
                setAuthError("");
                setConfirmPassword("");
              }}
              className="text-[#1a73e8] text-[14px] font-medium hover:bg-[#f8f9ff] px-2 py-1 rounded-[4px]"
            >
              {authMode === "login" ? "Create account" : "Sign in instead"}
            </button>
            <button
              type="submit"
              disabled={authLoading}
              className="bg-[#1a73e8] hover:bg-[#185abc] hover:shadow-[0_1px_2px_rgba(60,64,67,0.3),0_1px_3px_1px_rgba(60,64,67,0.15)] text-white text-[14px] font-medium px-6 py-2 rounded-[4px] disabled:opacity-50 min-w-[80px] h-9"
            >
              {authLoading ? <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin inline-block"></span> : authMode === "login" ? "Next" : "Next"}
            </button>
          </div>
        </form>

        <div className="flex items-center gap-4 my-6">
          <div className="flex-1 h-[1px] bg-[#dadce0]"></div>
          <span className="text-[#5f6368] text-[14px]">or</span>
          <div className="flex-1 h-[1px] bg-[#dadce0]"></div>
        </div>

        <button
          onClick={handleGoogleLogin}
          className="w-full flex items-center justify-center gap-3 py-2.5 border border-[#dadce0] rounded-[4px] hover:bg-[#f8f9fa] text-[#3c4043] text-[14px] font-medium"
        >
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24s.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/><path fill="none" d="M0 0h48v48H0z"/></svg>
          Continue with Google
        </button>

        <div className="mt-8 text-[12px] text-[#5f6368] leading-[1.4] text-center">
          Smart Document Chatbot — Enterprise Agentic CRAG Platform
        </div>
      </div>
    </div>
  );
}
