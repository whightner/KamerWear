import "server-only";

import { apiUrl } from "@/lib/api-config";

// Server-side calls to the FastAPI auth/account endpoints. Only used by Server
// Actions, the proxy and Server Components: tokens never reach browser JS.

export interface Profile {
  first_name: string;
  last_name: string;
  phone: string | null;
  avatar_path: string | null;
}

export interface User {
  id: number;
  email: string;
  role: "customer" | "admin";
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  profile: Profile;
}

export interface AuthTokens {
  user: User;
  access_token: string;
  refresh_token: string;
  access_token_expires_in: number;
  refresh_token_expires_in: number;
}

export interface ApiFailure {
  ok: false;
  status: number;
  /** Backend error code, or "unavailable" when the API could not be reached. */
  code: string;
  message: string;
  fields: Record<string, string>;
}

export type ApiResult<T> = { ok: true; data: T } | ApiFailure;

async function call<T>(
  path: string,
  init: { method?: string; body?: unknown; accessToken?: string; clientIp?: string | null },
): Promise<ApiResult<T>> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (init.accessToken) headers.Authorization = `Bearer ${init.accessToken}`;
  // Lets the API rate-limit by the real browser IP (it only trusts this from us).
  if (init.clientIp) headers["X-Forwarded-For"] = init.clientIp;

  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: init.method ?? "GET",
      headers,
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });
  } catch (cause) {
    if (!(cause instanceof TypeError)) throw cause;
    return {
      ok: false,
      status: 0,
      code: "unavailable",
      message: "We couldn't reach KamerWear right now. Please try again.",
      fields: {},
    };
  }

  if (response.status === 204) return { ok: true, data: undefined as T };
  const body: unknown = await response.json().catch(() => null);
  if (response.ok) return { ok: true, data: body as T };

  const detail = (body as { detail?: unknown } | null)?.detail;
  const structured =
    detail && typeof detail === "object" && "code" in detail
      ? (detail as { code: string; message?: string; fields?: Record<string, string> })
      : null;
  return {
    ok: false,
    status: response.status,
    code: structured?.code ?? "error",
    message: structured?.message ?? "Something went wrong. Please try again.",
    fields: structured?.fields ?? {},
  };
}

export const authApi = {
  login: (email: string, password: string, clientIp: string | null) =>
    call<AuthTokens>("/auth/login", {
      method: "POST",
      body: { email, password },
      clientIp,
    }),
  register: (
    data: {
      email: string;
      password: string;
      first_name: string;
      last_name: string;
      phone: string | null;
    },
    clientIp: string | null,
  ) => call<AuthTokens>("/auth/register", { method: "POST", body: data, clientIp }),
  refresh: (refreshToken: string) =>
    call<AuthTokens>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  logout: (refreshToken: string) =>
    call<void>("/auth/logout", {
      method: "POST",
      body: { refresh_token: refreshToken },
    }),
  me: (accessToken: string) => call<User>("/users/me", { accessToken }),
  updateMe: (
    accessToken: string,
    data: { first_name: string; last_name: string; phone: string | null },
  ) => call<User>("/users/me", { method: "PATCH", body: data, accessToken }),
  changePassword: (
    accessToken: string,
    data: { current_password: string; new_password: string },
  ) =>
    call<void>("/users/me/change-password", {
      method: "POST",
      body: data,
      accessToken,
    }),
};
