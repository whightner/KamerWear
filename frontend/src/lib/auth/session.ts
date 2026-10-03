import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { commerceApi } from "@/lib/commerce/api";
import type { Cart } from "@/lib/commerce/types";
import { authApi, type User } from "./api";
import { ACCESS_COOKIE } from "./cookies";

/** The access token from the HttpOnly cookie (server-side only). */
export async function getAccessToken(): Promise<string | undefined> {
  return (await cookies()).get(ACCESS_COOKIE)?.value;
}

/**
 * The signed-in user for this request, or null.
 *
 * Asks FastAPI (`GET /users/me`), so a revoked session (logout, password
 * change) is noticed right away. Cached per request: the header and the page
 * share one API call. Never throws: an unreachable API counts as signed out.
 */
export const getCurrentUser = cache(async (): Promise<User | null> => {
  const accessToken = await getAccessToken();
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

/**
 * The signed-in customer's saved cart. "unavailable" when the API couldn't be
 * reached, null when nobody is signed in.
 */
export const getServerCart = cache(async (): Promise<Cart | "unavailable" | null> => {
  const accessToken = await getAccessToken();
  if (!accessToken) return null;
  const result = await commerceApi.cart(accessToken);
  if (result.ok) return result.data;
  return result.status === 401 ? null : "unavailable";
});
