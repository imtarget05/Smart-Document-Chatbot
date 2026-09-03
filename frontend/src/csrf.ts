import { API_BASE_URL } from "./context/apiConfig";

let csrfToken: string | null = null;

export async function bootstrapCsrfToken(): Promise<void> {
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const response = await fetch(`${API_BASE_URL}/csrf`, { method: "GET", credentials: "include" });
      if (!response.ok) {
        if (attempt < 2) await new Promise((r) => setTimeout(r, 3000));
        continue;
      }
      const data = (await response.json()) as { token?: string };
      csrfToken = data.token ?? null;
      if (csrfToken) return;
    } catch {
      if (attempt < 2) await new Promise((r) => setTimeout(r, 3000));
    }
  }
  csrfToken = null;
}

function getCsrfFromCookie(): string | null {
  const match = document.cookie.match(/(?:^|; )XSRF-TOKEN=([^;]*)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export function csrfHeaders(): Record<string, string> {
  const token = csrfToken || getCsrfFromCookie();
  return token ? { "X-XSRF-TOKEN": token } : {};
}

/** Returns CSRF headers, fetching the token on demand if not bootstrapped yet
 *  (e.g. the first bootstrap failed because the backend was cold-starting).
 *  Pass force=true to refetch even if a token is cached (stale-token retry). */
export async function ensureCsrfHeaders(force = false): Promise<Record<string, string>> {
  if (force || !csrfToken) await bootstrapCsrfToken();
  return csrfHeaders();
}