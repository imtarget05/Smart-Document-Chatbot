import { API_BASE_URL } from "./context/apiConfig";

let csrfToken: string | null = null;

export async function bootstrapCsrfToken(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/csrf`, { method: "GET" });
    if (!response.ok) return;
    const data = (await response.json()) as { token?: string };
    csrfToken = data.token ?? null;
  } catch {
    csrfToken = null;
  }
}

export function csrfHeaders(): Record<string, string> {
  return csrfToken ? { "X-XSRF-TOKEN": csrfToken } : {};
}

/** Returns CSRF headers, fetching the token on demand if not bootstrapped yet
 *  (e.g. the first bootstrap failed because the backend was cold-starting). */
export async function ensureCsrfHeaders(): Promise<Record<string, string>> {
  if (!csrfToken) await bootstrapCsrfToken();
  return csrfHeaders();
}