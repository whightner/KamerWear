import "server-only";

import { cookies } from "next/headers";
import { apiUrl } from "@/lib/api-config";
import { ACCESS_COOKIE, secondsUntilExpiry } from "@/lib/auth/cookies";

// For route handlers that the browser calls directly (polling, sending chat
// messages). They forward the request to FastAPI with the access token from
// the HttpOnly cookie. Route handlers skip the proxy, so they don't renew the
// session: an almost-expired token gets 401 session_expired and the page
// calls the ensureSession Server Action, then retries once.

function error(status: number, code: string, message: string) {
  return Response.json({ detail: { code, message } }, { status });
}

export async function forwardJson(
  path: string,
  init: { method?: string; body?: unknown } = {},
): Promise<Response> {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (secondsUntilExpiry(access) <= 10) {
    return error(401, "session_expired", "Your session has expired. Please log in again.");
  }
  let response: Response;
  try {
    response = await fetch(apiUrl(path), {
      method: init.method ?? "GET",
      headers: {
        Accept: "application/json",
        Authorization: `Bearer ${access}`,
        ...(init.body !== undefined ? { "Content-Type": "application/json" } : {}),
      },
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
      cache: "no-store",
    });
  } catch {
    return error(503, "unavailable", "We couldn't reach KamerWear right now.");
  }
  const body = await response.json().catch(() => null);
  if (body === null) return error(502, "unavailable", "Unexpected response.");
  return Response.json(body, { status: response.status });
}

/** The JSON body of a browser request, limited in size. */
export async function readBody(request: Request, maxBytes = 16 * 1024): Promise<unknown> {
  const length = Number(request.headers.get("content-length") ?? "0");
  if (length > maxBytes) return undefined;
  const text = await request.text();
  if (text.length > maxBytes) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return undefined;
  }
}
