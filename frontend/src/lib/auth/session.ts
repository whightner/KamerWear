import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { authApi, type User } from "./api";
import { ACCESS_COOKIE } from "./cookies";

/**
 * The signed-in user for this request, or null.
 *
 * Asks FastAPI (`GET /users/me`), so a revoked session (logout, password
 * change) is noticed right away. Cached per request: the header and the page
 * share one API call. Never throws: an unreachable API counts as signed out.
 */
export const getCurrentUser = cache(async (): Promise<User | null> => {
  const accessToken = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!accessToken) return null;
  const result = await authApi.me(accessToken);
  return result.ok ? result.data : null;
});

/** For protected pages: the signed-in user, or a redirect to /login?next=… */
export async function requireUser(nextPath: string): Promise<User> {
  const user = await getCurrentUser();
  if (!user) redirect(`/login?next=${encodeURIComponent(nextPath)}`);
  return user;
}
