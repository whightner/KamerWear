"use server";

// Server Actions for login, registration, logout and the account pages.
//
// CSRF: Server Actions only accept POST, and Next.js rejects a request whose
// Origin header doesn't match the Host. The auth cookies are also SameSite=Lax,
// so other sites can't send them with a cross-site POST.

import { cookies, headers } from "next/headers";
import { redirect } from "next/navigation";
import { refresh } from "next/cache";
import { mergeGuestCart, withCartNotice } from "@/lib/commerce/guest-cart";
import { authApi, type ApiFailure, type AuthTokens } from "./api";
import {
  ACCESS_COOKIE,
  REFRESH_COOKIE,
  authCookieOptions,
  safeNextPath,
} from "./cookies";

export interface FormState {
  /** Message shown above the form (role="alert"). */
  error?: string;
  /** Message shown after a successful save. */
  success?: string;
  /** Per-field messages, keyed by input name. */
  fields?: Record<string, string>;
  /** Submitted values (never passwords), so inputs refill after React resets the form. */
  values?: Record<string, string>;
}

const PASSWORD_MIN_LENGTH = 10;

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

/** Passwords are passed through exactly as typed: no trimming, no truncation. */
function password(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value : "";
}

async function clientIp(): Promise<string | null> {
  const forwarded = (await headers()).get("x-forwarded-for");
  return forwarded?.split(",")[0]?.trim() || null;
}

async function setSession(tokens: AuthTokens) {
  const jar = await cookies();
  jar.set(
    ACCESS_COOKIE,
    tokens.access_token,
    authCookieOptions(tokens.access_token_expires_in),
  );
  jar.set(
    REFRESH_COOKIE,
    tokens.refresh_token,
    authCookieOptions(tokens.refresh_token_expires_in),
  );
}

async function clearSession() {
  const jar = await cookies();
  jar.delete(ACCESS_COOKIE);
  jar.delete(REFRESH_COOKIE);
}

/** Ends the current session in FastAPI (if any) and removes the cookies. */
async function endCurrentSession() {
  const refreshToken = (await cookies()).get(REFRESH_COOKIE)?.value;
  if (refreshToken) await authApi.logout(refreshToken);
  await clearSession();
}

function generalError(failure: ApiFailure): string {
  switch (failure.code) {
    case "invalid_credentials":
      return "Email or password is incorrect.";
    case "inactive_account":
      return "This account has been deactivated. Please contact support.";
    case "too_many_attempts":
      return "Too many attempts. Please wait a few minutes and try again.";
    case "unavailable":
      return "We couldn't reach KamerWear right now. Please try again.";
    case "validation_error":
      return "Please check the highlighted fields.";
    default:
      return failure.message;
  }
}

async function accessTokenOrLogin(nextPath: string): Promise<string> {
  const token = (await cookies()).get(ACCESS_COOKIE)?.value;
  if (!token) redirect(`/login?next=${encodeURIComponent(nextPath)}&reason=expired`);
  return token;
}

async function sessionExpired(nextPath: string): Promise<never> {
  await clearSession();
  redirect(`/login?next=${encodeURIComponent(nextPath)}&reason=expired`);
}

export async function loginAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const email = text(formData, "email");
  const pass = password(formData, "password");
  const next = safeNextPath(formData.get("next"));
  const values = { email };

  const fields: Record<string, string> = {};
  if (!email) fields.email = "Enter your email address.";
  if (!pass) fields.password = "Enter your password.";
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields, values };
  }

  const result = await authApi.login(email, pass, await clientIp());
  if (!result.ok) {
    // Field-level errors would reveal nothing useful here; keep one message.
    return { error: generalError(result), values };
  }

  await endCurrentSession(); // signing in again replaces any previous session
  await setSession(result.data);
  const adjusted = await mergeGuestCart(result.data.access_token, formData.get("guest_cart"));
  redirect(adjusted ? withCartNotice(next) : next);
}

export async function registerAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const values = {
    first_name: text(formData, "first_name"),
    last_name: text(formData, "last_name"),
    email: text(formData, "email"),
    phone: text(formData, "phone"),
  };
  const pass = password(formData, "password");
  const confirm = password(formData, "confirm_password");
  const next = safeNextPath(formData.get("next"));

  const fields: Record<string, string> = {};
  if (!values.first_name) fields.first_name = "Enter your first name.";
  if (!values.last_name) fields.last_name = "Enter your last name.";
  if (!values.email) fields.email = "Enter your email address.";
  if (pass.length < PASSWORD_MIN_LENGTH) {
    fields.password = `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
  }
  if (confirm !== pass) fields.confirm_password = "Passwords don't match.";
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields, values };
  }

  const result = await authApi.register(
    { ...values, phone: values.phone || null, password: pass },
    await clientIp(),
  );
  if (!result.ok) {
    if (result.code === "email_already_registered") {
      return {
        error: "Please check the highlighted fields.",
        fields: { email: "An account with this email already exists. Try logging in." },
        values,
      };
    }
    return { error: generalError(result), fields: result.fields, values };
  }

  await endCurrentSession();
  await setSession(result.data);
  const adjusted = await mergeGuestCart(result.data.access_token, formData.get("guest_cart"));
  redirect(adjusted ? withCartNotice(next) : next);
}

export async function logoutAction() {
  await endCurrentSession();
  redirect("/");
}

export async function updateProfileAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const values = {
    first_name: text(formData, "first_name"),
    last_name: text(formData, "last_name"),
    phone: text(formData, "phone"),
  };
  const fields: Record<string, string> = {};
  if (!values.first_name) fields.first_name = "Enter your first name.";
  if (!values.last_name) fields.last_name = "Enter your last name.";
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields, values };
  }

  const token = await accessTokenOrLogin("/account/profile");
  const result = await authApi.updateMe(token, {
    ...values,
    phone: values.phone || null,
  });
  if (!result.ok) {
    if (result.status === 401) return sessionExpired("/account/profile");
    return { error: generalError(result), fields: result.fields, values };
  }

  refresh(); // re-render the header greeting with the new name
  const profile = result.data.profile;
  return {
    success: "Your profile has been saved.",
    values: {
      first_name: profile.first_name,
      last_name: profile.last_name,
      phone: profile.phone ?? "",
    },
  };
}

export async function changePasswordAction(
  _previous: FormState,
  formData: FormData,
): Promise<FormState> {
  const current = password(formData, "current_password");
  const next = password(formData, "new_password");
  const confirm = password(formData, "confirm_password");

  const fields: Record<string, string> = {};
  if (!current) fields.current_password = "Enter your current password.";
  if (next.length < PASSWORD_MIN_LENGTH) {
    fields.new_password = `Use at least ${PASSWORD_MIN_LENGTH} characters.`;
  } else if (next === current) {
    fields.new_password = "Choose a password different from your current one.";
  }
  if (confirm !== next) fields.confirm_password = "Passwords don't match.";
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields };
  }

  const token = await accessTokenOrLogin("/account/profile");
  const result = await authApi.changePassword(token, {
    current_password: current,
    new_password: next,
  });
  if (!result.ok) {
    if (result.status === 401) return sessionExpired("/account/profile");
    if (result.code === "invalid_current_password") {
      return {
        error: "Please check the highlighted fields.",
        fields: { current_password: "Your current password is incorrect." },
      };
    }
    return { error: generalError(result), fields: result.fields };
  }

  return {
    success: "Your password has been changed. Other devices have been signed out.",
  };
}
