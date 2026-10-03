"use server";

// Server Actions for the Fit Profile (save/confirm and delete). Photos never
// pass through here: they go to the /api/fit/estimate route handler.

import { redirect } from "next/navigation";
import { getAccessToken, getCurrentUser } from "@/lib/auth/session";
import { fitApi } from "./api";

export interface FitFormState {
  error?: string;
  fields?: Record<string, string>;
}

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function optionalInt(value: string): number | null {
  return value === "" ? null : Number.parseInt(value, 10);
}

/**
 * Saves what the customer confirmed (from the review step or the account page).
 * With an estimate id, the API copies the estimated dimensions from that
 * estimate; the browser never sends measurements.
 */
export async function saveFitProfile(
  _previous: FitFormState,
  formData: FormData,
): Promise<FitFormState> {
  const token = await getAccessToken();
  if (!token) redirect("/login?next=/fit&reason=expired");

  const height = Number.parseInt(text(formData, "height_cm"), 10);
  const body = {
    estimate_id: optionalInt(text(formData, "estimate_id")),
    height_cm: Number.isFinite(height) ? height : 0,
    fit_preference: text(formData, "fit_preference") || "regular",
    top_size: text(formData, "top_size") || null,
    bottom_size: text(formData, "bottom_size") || null,
    shoe_size_eu: optionalInt(text(formData, "shoe_size_eu")),
  };
  const result = await fitApi.save(token, body);
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=/account/fit-profile&reason=expired");
    if (result.code === "validation_error") {
      return { error: "Please check the highlighted values.", fields: result.fields };
    }
    return { error: result.message };
  }
  redirect("/account/fit-profile?saved=1");
}

export async function deleteFitProfile(): Promise<FitFormState> {
  const token = await getAccessToken();
  if (!token) redirect("/login?next=/account/fit-profile&reason=expired");
  const result = await fitApi.remove(token);
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=/account/fit-profile&reason=expired");
    return { error: result.message };
  }
  redirect("/account/fit-profile?deleted=1");
}

/**
 * Called by the photo step before retrying an upload whose access token had
 * expired: like every Server Action request, it passes through the proxy,
 * which renews the session once.
 */
export async function ensureFitSession(): Promise<boolean> {
  return (await getCurrentUser()) !== null;
}
