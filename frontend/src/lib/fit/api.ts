import "server-only";

import { call } from "@/lib/api/server";
import { getAccessToken } from "@/lib/auth/session";
import type { FitProfile, ProductFitState, ProductFitRecommendation } from "./types";

// Server-side Smart Fit calls (the access token stays on the server).

export const fitApi = {
  profile: (accessToken: string) => call<FitProfile>("/fit/profile", { accessToken }),
  save: (accessToken: string, body: Record<string, unknown>) =>
    call<FitProfile>("/fit/profile", { method: "PUT", body, accessToken }),
  remove: (accessToken: string) =>
    call<void>("/fit/profile", { method: "DELETE", accessToken }),
};

/** The signed-in customer's Fit Profile: null if none, "unavailable" on errors. */
export async function getFitProfile(): Promise<FitProfile | null | "unavailable"> {
  const token = await getAccessToken();
  if (!token) return null;
  const result = await fitApi.profile(token);
  if (result.ok) return result.data;
  return result.code === "fit_profile_not_found" ? null : "unavailable";
}

/**
 * The product-page recommendation. Never throws: a Smart Fit problem must not
 * break the product page, so failures become { status: "error" }.
 */
export async function getProductFit(slug: string): Promise<ProductFitState> {
  const token = await getAccessToken();
  if (!token) return { status: "signed_out" };
  const result = await call<ProductFitRecommendation>(
    `/products/${encodeURIComponent(slug)}/fit-recommendation`,
    { accessToken: token },
  );
  if (result.ok) return result.data;
  return result.status === 401 ? { status: "signed_out" } : { status: "error" };
}
