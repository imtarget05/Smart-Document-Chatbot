// Use relative path in development so Vite proxy handles requests.
// In production, set VITE_API_URL to the full backend URL.
export const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string) || "/api";
