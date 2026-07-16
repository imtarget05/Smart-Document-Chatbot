import { useState } from 'react';
import { useAuth, API_BASE_URL } from '../context/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!authUsername.trim() || !authPassword.trim()) {
      setAuthError('Please fill in all fields');
      return;
    }
    setAuthError('');
    setAuthLoading(true);

    try {
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/register';
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: authUsername, password: authPassword }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Authentication failed');
      }

      const data = await response.json();
      login(data.token, data.username, data.role);

      setAuthUsername('');
      setAuthPassword('');
    } catch (err: any) {
      setAuthError(err.message || 'Something went wrong');
    } finally {
      setAuthLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-tr from-slate-900 via-indigo-950 to-slate-900 p-6 font-sans">
      <div className="w-full max-w-md bg-white/5 backdrop-blur-xl border border-white/10 rounded-3xl p-8 shadow-2xl text-white">
        <div className="text-center mb-8">
          <span className="text-4xl">🔮</span>
          <h2 className="text-2xl font-bold mt-3 bg-gradient-to-r from-indigo-200 to-white bg-clip-text text-transparent">Smart Doc Chatbot</h2>
          <p className="text-xs text-indigo-200/60 mt-1.5 font-semibold">Enterprise Agentic CRAG Platform</p>
        </div>

        <div className="flex bg-white/5 p-1 rounded-2xl mb-6 border border-white/5">
          <button
            onClick={() => { setAuthMode('login'); setAuthError(''); }}
            className={`flex-1 text-center py-2.5 text-xs font-bold rounded-xl transition-all duration-300 ${
              authMode === 'login'
                ? 'bg-white text-indigo-950 shadow-md'
                : 'text-white/60 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => { setAuthMode('register'); setAuthError(''); }}
            className={`flex-1 text-center py-2.5 text-xs font-bold rounded-xl transition-all duration-300 ${
              authMode === 'register'
                ? 'bg-white text-indigo-950 shadow-md'
                : 'text-white/60 hover:text-white'
            }`}
          >
            Create Account
          </button>
        </div>

        <form onSubmit={handleAuthSubmit} className="space-y-4">
          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-indigo-200/70 mb-1.5">Username</label>
            <input
              type="text"
              value={authUsername}
              onChange={(e) => setAuthUsername(e.target.value)}
              placeholder="Enter username"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-sm font-semibold text-white placeholder-white/30 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/40 transition duration-200"
              required
            />
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-indigo-200/70 mb-1.5">Password</label>
            <input
              type="password"
              value={authPassword}
              onChange={(e) => setAuthPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-sm font-semibold text-white placeholder-white/30 focus:outline-none focus:border-white/40 focus:ring-1 focus:ring-white/40 transition duration-200"
              required
            />
          </div>

          {authError && (
            <p className="text-rose-400 text-xs font-bold bg-rose-500/10 border border-rose-500/20 px-3.5 py-2.5 rounded-xl">
              ⚠️ {authError}
            </p>
          )}

          <button
            type="submit"
            disabled={authLoading}
            className="w-full py-3.5 bg-white text-indigo-950 hover:bg-indigo-50 font-bold text-xs rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 flex items-center justify-center"
          >
            {authLoading ? (
              <span className="w-4 h-4 border-2 border-indigo-950 border-t-transparent rounded-full animate-spin"></span>
            ) : authMode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}