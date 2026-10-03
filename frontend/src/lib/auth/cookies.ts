// Auth cookie names and options, shared by Server Actions and the proxy.
//
// Tokens live only in HttpOnly cookies on the Next.js origin: browser
// JavaScript can't read them, and they are never put in localStorage,
// sessionStorage or React state. The Next.js server forwards the access token
// to FastAPI as a Bearer header.

export const ACCESS_COOKIE = "kw_access";
export const REFRESH_COOKIE = "kw_refresh";

/** Secure (HTTPS-only) in production; set AUTH_COOKIE_SECURE=true|false to override. */
function secureCookies(): boolean {
  const override = process.env.AUTH_COOKIE_SECURE;
  if (override === "true") return true;
  if (override === "false") return false;
  return process.env.NODE_ENV === "production";
}

export function authCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    secure: secureCookies(),
    // Lax: sent on top-level navigation from other sites, never on cross-site
    // POSTs (forms/fetch), which is what a CSRF attack would need.
    sameSite: "lax" as const,
    path: "/",
    maxAge: maxAgeSeconds,
  };
}

/** Seconds until a JWT's `exp`, read without verifying (FastAPI verifies tokens). */
export function secondsUntilExpiry(token: string | undefined): number {
  if (!token) return 0;
  try {
    const payload = JSON.parse(
      Buffer.from(token.split(".")[1] ?? "", "base64url").toString("utf8"),
    ) as { exp?: number };
    return typeof payload.exp === "number"
      ? payload.exp - Math.floor(Date.now() / 1000)
      : 0;
  } catch {
    return 0;
  }
}

/** Only same-site relative paths are allowed as post-login destinations. */
export function safeNextPath(value: unknown, fallback = "/account"): string {
  if (typeof value !== "string") return fallback;
  if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\")) {
    return fallback;
  }
  return value;
}
