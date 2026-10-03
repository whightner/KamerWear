import { cookies } from "next/headers";
import { apiUrl } from "@/lib/api-config";
import { ACCESS_COOKIE, secondsUntilExpiry } from "@/lib/auth/cookies";

// Forwards the Smart Fit photos to FastAPI with the customer's access token
// (read from the HttpOnly cookie on the server). Nothing is stored: the files
// pass through in memory. FastAPI does the real validation and the estimate.
//
// Route handlers skip the proxy, so this one doesn't renew sessions itself:
// an almost-expired token gets 401 session_expired, the page calls a Server
// Action (which goes through the proxy's single refresh) and retries once.

const MAX_BYTES = 8 * 1024 * 1024;

function error(status: number, code: string, message: string, photo?: string) {
  return Response.json({ detail: { code, message, photo } }, { status });
}

export async function POST(request: Request) {
  const access = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (secondsUntilExpiry(access) <= 10) {
    return error(401, "session_expired", "Your session has expired. Please log in again.");
  }
  const length = Number(request.headers.get("content-length") ?? "0");
  if (length > 2 * MAX_BYTES + 64 * 1024) {
    return error(413, "fit_image_too_large", "The photos are too large. Each must be under 8 MB.");
  }
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return error(400, "invalid_fit_image", "Add a front photo.", "front");
  }

  const upstream = new FormData();
  for (const view of ["front", "side"] as const) {
    const file = form.get(view);
    if (!(file instanceof File) || file.size === 0) continue;
    if (file.size > MAX_BYTES) {
      return error(413, "fit_image_too_large", `The ${view} photo is larger than 8 MB.`, view);
    }
    upstream.set(view, file, file.name || `${view}-photo`);
  }
  if (!upstream.has("front")) {
    return error(400, "invalid_fit_image", "Add a front photo.", "front");
  }
  upstream.set("height_cm", String(form.get("height_cm") ?? ""));
  upstream.set("fit_preference", String(form.get("fit_preference") ?? "regular"));

  let response: Response;
  try {
    response = await fetch(apiUrl("/fit/estimate"), {
      method: "POST",
      body: upstream,
      headers: { Accept: "application/json", Authorization: `Bearer ${access}` },
      cache: "no-store",
    });
  } catch {
    return error(503, "unavailable", "We couldn't reach KamerWear right now. Please try again.");
  }
  const body = await response.json().catch(() => null);
  if (body === null) {
    return error(503, "fit_service_unavailable", "Photo sizing is unavailable right now.");
  }
  return Response.json(body, { status: response.status });
}
