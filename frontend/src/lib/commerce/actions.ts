"use server";

// Server Actions for the cart, addresses and checkout. They run on the Next.js
// server, read the access token from the HttpOnly cookie and call FastAPI,
// which decides ownership, prices, stock and totals.
//
// CSRF: Server Actions are POST-only and Next.js checks that the Origin
// matches the host; the auth cookies are SameSite=Lax.

import { refresh, revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import type { ApiFailure } from "@/lib/api/server";
import { getAccessToken } from "@/lib/auth/session";
import { commerceApi } from "./api";
import type { Address, AddressInput, Cart, PaymentMethod, Quote } from "./types";

export type ActionResult<T> =
  | { ok: true; data: T }
  | { ok: false; code: string; message: string };

const PAYMENT_METHODS: PaymentMethod[] = ["mobile_money", "card", "cash_on_delivery"];

function failure(result: ApiFailure): { ok: false; code: string; message: string } {
  if (result.status === 401) {
    return {
      ok: false,
      code: "session_expired",
      message: "Your session has expired. Please log in again.",
    };
  }
  return { ok: false, code: result.code, message: result.message };
}

async function token(): Promise<string | null> {
  return (await getAccessToken()) ?? null;
}

const SIGNED_OUT = {
  ok: false as const,
  code: "session_expired",
  message: "Your session has expired. Please log in again.",
};

// --- Cart ----------------------------------------------------------------------

export async function addToCartAction(
  variantId: number,
  quantity: number,
): Promise<ActionResult<Cart>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.addToCart(accessToken, variantId, quantity);
  return result.ok ? result : failure(result);
}

export async function updateCartItemAction(
  itemId: number,
  quantity: number,
): Promise<ActionResult<Cart>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.updateCartItem(accessToken, itemId, quantity);
  return result.ok ? result : failure(result);
}

export async function removeCartItemAction(itemId: number): Promise<ActionResult<Cart>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.removeCartItem(accessToken, itemId);
  return result.ok ? result : failure(result);
}

// --- Addresses -------------------------------------------------------------------

export interface AddressFormState {
  error?: string;
  success?: string;
  fields?: Record<string, string>;
  values?: Record<string, string>;
  /** The saved address (lets checkout select it straight away). */
  address?: Address;
}

const ADDRESS_FIELDS = [
  "label",
  "recipient_name",
  "phone",
  "region",
  "city",
  "quarter",
  "street_or_landmark",
] as const;

const REQUIRED_MESSAGES: Record<(typeof ADDRESS_FIELDS)[number], string> = {
  label: "Give this address a name, e.g. Home.",
  recipient_name: "Enter the name of the person receiving the order.",
  phone: "Enter a phone number the courier can call.",
  region: "Choose a region.",
  city: "Enter the city.",
  quarter: "Enter the quarter or neighbourhood.",
  street_or_landmark: "Describe the street or a landmark near the address.",
};

export async function saveAddressAction(
  _previous: AddressFormState,
  formData: FormData,
): Promise<AddressFormState> {
  const values: Record<string, string> = {};
  for (const field of ADDRESS_FIELDS) {
    const value = formData.get(field);
    values[field] = typeof value === "string" ? value.trim() : "";
  }
  const isDefault = formData.get("is_default") === "on";
  values.is_default = isDefault ? "on" : "";
  const id = Number(formData.get("id")) || null;

  const fields: Record<string, string> = {};
  for (const field of ADDRESS_FIELDS) {
    if (!values[field]) fields[field] = REQUIRED_MESSAGES[field];
  }
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields, values };
  }

  const accessToken = await token();
  if (!accessToken) redirect("/login?reason=expired");
  const data = { ...values, is_default: isDefault } as unknown as AddressInput;
  if (id && !isDefault) delete (data as Partial<AddressInput>).is_default;
  const result = id
    ? await commerceApi.updateAddress(accessToken, id, data)
    : await commerceApi.createAddress(accessToken, data);
  if (!result.ok) {
    if (result.status === 401) redirect("/login?reason=expired");
    return {
      error:
        result.code === "validation_error"
          ? "Please check the highlighted fields."
          : result.message,
      fields: result.fields,
      values,
    };
  }
  refresh();
  return { success: id ? "Address updated." : "Address saved.", address: result.data };
}

export async function deleteAddressAction(id: number): Promise<ActionResult<null>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.deleteAddress(accessToken, id);
  if (!result.ok) return failure(result);
  refresh();
  return { ok: true, data: null };
}

export async function setDefaultAddressAction(id: number): Promise<ActionResult<Address>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.updateAddress(accessToken, id, { is_default: true });
  if (!result.ok) return failure(result);
  refresh();
  return result;
}

// --- Checkout ------------------------------------------------------------------

export async function quoteAction(
  addressId: number | null,
  paymentMethod: PaymentMethod | null,
): Promise<ActionResult<Quote>> {
  const accessToken = await token();
  if (!accessToken) return SIGNED_OUT;
  const result = await commerceApi.quote(accessToken, addressId, paymentMethod);
  return result.ok ? result : failure(result);
}

export interface PlaceOrderState {
  error?: string;
  /** A fresh server quote when prices, fees or stock changed. */
  quote?: Quote;
}

export async function placeOrderAction(
  _previous: PlaceOrderState,
  formData: FormData,
): Promise<PlaceOrderState> {
  const addressId = Number(formData.get("address_id")) || null;
  const method = formData.get("payment_method") as PaymentMethod | null;
  const expectedTotal = Number(formData.get("expected_total"));
  const key = String(formData.get("idempotency_key") ?? "");

  if (!addressId) return { error: "Choose a delivery address." };
  if (!method || !PAYMENT_METHODS.includes(method)) {
    return { error: "Choose a payment method." };
  }

  const accessToken = await token();
  if (!accessToken) redirect("/login?next=/checkout&reason=expired");
  const result = await commerceApi.placeOrder(
    accessToken,
    { address_id: addressId, payment_method: method, expected_total: expectedTotal },
    key,
  );
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=/checkout&reason=expired");
    // Show the error together with an up-to-date quote. Nothing was ordered.
    const fresh = await commerceApi.quote(accessToken, addressId, method);
    const error =
      result.code === "unavailable"
        ? "We couldn't place your order because KamerWear is unreachable. Nothing was charged or ordered. Please try again."
        : result.code === "address_not_found"
          ? "This address is no longer available. Please choose another one."
          : result.message;
    return { error, quote: fresh.ok ? fresh.data : undefined };
  }

  // The cart is now empty: re-render the header and cart everywhere.
  revalidatePath("/", "layout");
  redirect(`/orders/${encodeURIComponent(result.data.order_number)}?placed=1`);
}
