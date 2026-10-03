import "server-only";

import { apiUrl } from "@/lib/api-config";

// Server-side JSON calls to FastAPI, used by Server Actions, the proxy and
// Server Components. The access token (from the HttpOnly cookie) is sent as a
// Bearer header; it never reaches browser JavaScript.

export interface ApiFailure {
  ok: false;
  status: number;
  /** Backend error code, or "unavailable" when the API could not be reached. */
  code: string;
  message: string;
  fields: Record<string, string>;
  /** Any other fields of the error body (e.g. `items` for insufficient_stock). */
  extra: Record<string, unknown>;
}

export type ApiResult<T> = { ok: true; data: T } | ApiFailure;

export async function call<T>(
  path: string,
  init: {
    method?: string;
    body?: unknown;
    accessToken?: string;
    clientIp?: string | null;
    headers?: Record<string, string>;
  } = {},
): Promise<ApiResult<T>> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...init.headers,
  };
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
      extra: {},
    };
  }

  if (response.status === 204) return { ok: true, data: undefined as T };
  const body: unknown = await response.json().catch(() => null);
  if (response.ok) return { ok: true, data: body as T };

  const detail = (body as { detail?: unknown } | null)?.detail;
  const structured =
    detail && typeof detail === "object" && "code" in detail
      ? (detail as {
          code: string;
          message?: string;
          fields?: Record<string, string>;
        } & Record<string, unknown>)
      : null;
  return {
    ok: false,
    status: response.status,
    code: structured?.code ?? "error",
    message: structured?.message ?? "Something went wrong. Please try again.",
    fields: structured?.fields ?? {},
    extra: structured ?? {},
  };
}

