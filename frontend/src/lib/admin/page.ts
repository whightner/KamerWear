import "server-only";

import { getAccessToken, requireAdmin } from "@/lib/auth/session";

/**
 * Start of every admin page: the admin's access token, or null when the
 * visitor isn't an admin (the admin layout then shows "not authorized" and the
 * page renders nothing, so no admin data is fetched for customers).
 */
export async function adminToken(path: string): Promise<string | null> {
  const admin = await requireAdmin(path);
  if (!admin) return null;
  return (await getAccessToken()) ?? null;
}

/** First value of a search param. */
export function param(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}
