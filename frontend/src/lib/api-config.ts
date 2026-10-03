// Base URL of the KamerWear REST API, e.g. "http://localhost:8000/api/v1".
// Set NEXT_PUBLIC_API_URL in frontend/.env.local. Next.js inlines it at build time,
// so it must be read with this exact static `process.env.NEXT_PUBLIC_API_URL` lookup.
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
).replace(/\/+$/, "");

// Builds a full API URL from a path such as "/health".
export function apiUrl(path: string): string {
  return `${API_BASE_URL}/${path.replace(/^\/+/, "")}`;
}
