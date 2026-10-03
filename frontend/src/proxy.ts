import { NextResponse, type NextRequest } from "next/server";
import { authApi, type ApiResult, type AuthTokens } from "@/lib/auth/api";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  authCookieOptions,
  secondsUntilExpiry,
} from "@/lib/auth/cookies";

// Runs before every page request (and Server Action) to keep the session fresh:
// when the 15-minute access token is missing or about to expire, it is renewed
// with the refresh token, so pages render with a valid token. It also sends
// signed-out visitors of account, checkout, order, return, support and admin pages to /login. The
// pages still check the user themselves (requireUser); this is only the fast
// first check.

const REFRESH_MARGIN_SECONDS = 30;

// Refresh tokens are single-use. When the browser fires several requests at
// once (e.g. link prefetches), they must share one refresh call, or the
// second one would look like token reuse and end the session. This in-memory
// map works for the single Next.js server of the MVP.
const inflight = new Map<string, Promise<ApiResult<AuthTokens>>>();

function refreshOnce(refreshToken: string) {
  let pending = inflight.get(refreshToken);
  if (!pending) {
    pending = authApi.refresh(refreshToken);
    inflight.set(refreshToken, pending);
    // Keep the result briefly for requests that were already on their way.
    pending.finally(() => setTimeout(() => inflight.delete(refreshToken), 10_000));
  }
  return pending;
}

const PROTECTED = ["/account", "/checkout", "/orders", "/admin", "/returns", "/support"];

function isProtected(pathname: string) {
  return PROTECTED.some((base) => pathname === base || pathname.startsWith(`${base}/`));
}

function loginRedirect(request: NextRequest, reason?: string) {
  const url = new URL("/login", request.url);
  url.searchParams.set("next", request.nextUrl.pathname + request.nextUrl.search);
  if (reason) url.searchParams.set("reason", reason);
  return NextResponse.redirect(url);
}

export async function proxy(request: NextRequest) {
  const access = request.cookies.get(ACCESS_COOKIE)?.value;
  const refreshToken = request.cookies.get(REFRESH_COOKIE)?.value;
  const needsRefresh = secondsUntilExpiry(access) <= REFRESH_MARGIN_SECONDS;

  if (!needsRefresh) return NextResponse.next();

  if (!refreshToken) {
    return isProtected(request.nextUrl.pathname)
      ? loginRedirect(request)
      : NextResponse.next();
  }

  const result = await refreshOnce(refreshToken);

  if (result.ok) {
    const tokens = result.data;
    // Update the request so this render already uses the new access token...
    request.cookies.set(ACCESS_COOKIE, tokens.access_token);
    request.cookies.set(REFRESH_COOKIE, tokens.refresh_token);
    const response = NextResponse.next({ request: { headers: request.headers } });
    // ...and the browser so it keeps the new pair.
    response.cookies.set(
      ACCESS_COOKIE,
      tokens.access_token,
      authCookieOptions(tokens.access_token_expires_in),
    );
    response.cookies.set(
      REFRESH_COOKIE,
      tokens.refresh_token,
      authCookieOptions(tokens.refresh_token_expires_in),
    );
    return response;
  }

  // API unreachable: keep the cookies and let the page show its error state.
  if (result.code === "unavailable") return NextResponse.next();

  // The session is over (expired, logged out or revoked): forget it.
  request.cookies.delete(ACCESS_COOKIE);
  request.cookies.delete(REFRESH_COOKIE);
  const response = isProtected(request.nextUrl.pathname)
    ? loginRedirect(request, "expired")
    : NextResponse.next({ request: { headers: request.headers } });
  response.cookies.delete(ACCESS_COOKIE);
  response.cookies.delete(REFRESH_COOKIE);
  return response;
}

export const config = {
  // Pages and Server Actions only: skip static files, images and /api route
  // handlers (the image upload must not be buffered or cut off by the proxy).
  matcher: ["/((?!_next/static|_next/image|images/|favicon.ico|api/).*)"],
};
