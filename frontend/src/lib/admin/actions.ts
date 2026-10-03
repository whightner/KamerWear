"use server";

// Server Actions behind the admin forms. They only translate form fields into
// API calls; FastAPI checks the ADMIN role and every business rule (unique
// slugs and SKUs, price rules, stock never below reserved, order transitions).
//
// CSRF: Server Actions are POST-only with an Origin check, and the auth cookies
// are SameSite=Lax (see docs/architecture/auth.md).

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import type { ApiFailure } from "@/lib/api/server";
import { getAccessToken } from "@/lib/auth/session";
import { adminApi } from "./api";

export interface AdminFormState {
  error?: string;
  success?: string;
  fields?: Record<string, string>;
  /** Submitted values, so inputs refill after React resets the form. */
  values?: Record<string, string>;
  /** Changes on every result so client components can react to it. */
  at?: number;
}

export type AdminResult = { ok: true } | { ok: false; message: string };

async function token(): Promise<string> {
  const value = await getAccessToken();
  if (!value) redirect("/login?next=%2Fadmin&reason=expired");
  return value;
}

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

function checked(formData: FormData, name: string): boolean {
  return formData.get(name) === "on";
}

function values(formData: FormData): Record<string, string> {
  const result: Record<string, string> = {};
  formData.forEach((value, key) => {
    if (typeof value === "string" && !key.startsWith("$")) result[key] = value;
  });
  return result;
}

/** "28 500" / "28,500" → 28500. Empty → null. Anything else → NaN. */
function money(raw: string): number | null {
  const cleaned = raw.replace(/[\s,]/g, "").replace(/fcfa$/i, "");
  if (!cleaned) return null;
  return /^\d+$/.test(cleaned) ? Number(cleaned) : Number.NaN;
}

function wholeNumber(raw: string): number | null {
  if (!raw.trim()) return null;
  return /^\d+$/.test(raw.trim()) ? Number(raw.trim()) : Number.NaN;
}

function failure(result: ApiFailure, formData?: FormData): AdminFormState {
  if (result.status === 401) redirect("/login?next=%2Fadmin&reason=expired");
  const message =
    result.status === 403
      ? "Only administrators can do this."
      : result.code === "validation_error"
        ? "Please check the highlighted fields."
        : result.message;
  return {
    error: message,
    fields: result.fields,
    values: formData ? values(formData) : undefined,
    at: Date.now(),
  };
}

function simpleFailure(result: ApiFailure): AdminResult {
  if (result.status === 401) redirect("/login?next=%2Fadmin&reason=expired");
  return {
    ok: false,
    message: result.status === 403 ? "Only administrators can do this." : result.message,
  };
}

function invalid(fields: Record<string, string>, formData: FormData): AdminFormState {
  return {
    error: "Please check the highlighted fields.",
    fields,
    values: values(formData),
    at: Date.now(),
  };
}

// --- Categories ------------------------------------------------------------------

export async function saveCategoryAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const id = Number(formData.get("id")) || null;
  const body = {
    name: text(formData, "name"),
    slug: text(formData, "slug"),
    description: text(formData, "description"),
    is_active: checked(formData, "is_active"),
  };
  const fields: Record<string, string> = {};
  if (!body.name) fields.name = "Enter a name.";
  if (!body.slug) fields.slug = "Enter a slug, e.g. bags.";
  if (Object.keys(fields).length) return invalid(fields, formData);

  const t = await token();
  const result = id
    ? await adminApi.updateCategory(t, id, body)
    : await adminApi.createCategory(t, body);
  if (!result.ok) return failure(result, formData);
  refresh();
  return { success: id ? "Category saved." : `Category “${result.data.name}” created.`, at: Date.now() };
}

export async function setCategoryActiveAction(id: number, active: boolean): Promise<AdminResult> {
  const result = await adminApi.updateCategory(await token(), id, { is_active: active });
  if (!result.ok) return simpleFailure(result);
  refresh();
  return { ok: true };
}

// --- Products ------------------------------------------------------------------

export async function saveProductAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const id = Number(formData.get("id")) || null;
  const basePrice = money(text(formData, "base_price"));
  const compareAt = money(text(formData, "compare_at_price"));
  const fields: Record<string, string> = {};
  for (const [field, label] of [
    ["name", "Enter a product name."],
    ["slug", "Enter a slug, e.g. kribi-linen-shirt."],
    ["product_type", "Enter a product type, e.g. Shirt."],
  ] as const) {
    if (!text(formData, field)) fields[field] = label;
  }
  if (basePrice === null) fields.base_price = "Enter the price in FCFA, e.g. 28500.";
  else if (Number.isNaN(basePrice)) fields.base_price = "Use a whole number of FCFA, e.g. 28500.";
  if (Number.isNaN(compareAt)) {
    fields.compare_at_price = "Use a whole number of FCFA, or leave empty.";
  }
  if (Object.keys(fields).length) return invalid(fields, formData);

  const body = {
    name: text(formData, "name"),
    slug: text(formData, "slug"),
    category_id: Number(formData.get("category_id")),
    description: text(formData, "description"),
    gender: text(formData, "gender"),
    product_type: text(formData, "product_type"),
    base_price: basePrice,
    compare_at_price: compareAt,
    smart_fit: checked(formData, "smart_fit"),
    smart_fit_demo_size: text(formData, "smart_fit_demo_size") || null,
    is_new: checked(formData, "is_new"),
    featured: checked(formData, "featured"),
    search_keywords: text(formData, "search_keywords"),
  };
  // Activation is set when creating; afterwards it has its own button, so an
  // edit form opened earlier can't silently undo it.
  const payload = id ? body : { ...body, is_active: checked(formData, "is_active") };
  const t = await token();
  const result = id
    ? await adminApi.updateProduct(t, id, payload)
    : await adminApi.createProduct(t, payload);
  if (!result.ok) return failure(result, formData);
  if (!id) redirect(`/admin/products/${result.data.id}?created=1`);
  refresh();
  return { success: "Product saved.", at: Date.now() };
}

export async function setProductActiveAction(id: number, active: boolean): Promise<AdminResult> {
  const result = await adminApi.updateProduct(await token(), id, { is_active: active });
  if (!result.ok) return simpleFailure(result);
  refresh();
  return { ok: true };
}

// --- Variants ------------------------------------------------------------------

export async function saveVariantAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const productId = Number(formData.get("product_id"));
  const id = Number(formData.get("id")) || null;
  const priceOverride = money(text(formData, "price_override"));
  const onHand = wholeNumber(text(formData, "on_hand"));
  const fields: Record<string, string> = {};
  if (!text(formData, "sku")) fields.sku = "Enter a SKU, e.g. KLS-WHITE-M.";
  if (!text(formData, "color_name")) fields.color_name = "Enter a colour name.";
  if (Number.isNaN(priceOverride)) fields.price_override = "Use a whole number of FCFA, or leave empty.";
  if (!id && Number.isNaN(onHand)) fields.on_hand = "Use a whole number, e.g. 10.";
  if (Object.keys(fields).length) return invalid(fields, formData);

  const body: Record<string, unknown> = {
    sku: text(formData, "sku"),
    size: text(formData, "size") || null,
    color_name: text(formData, "color_name"),
    color_hex: text(formData, "color_hex"),
    price_override: priceOverride,
    is_active: checked(formData, "is_active"),
  };
  if (!id) body.on_hand = onHand ?? 0;
  const t = await token();
  const result = id
    ? await adminApi.updateVariant(t, id, body)
    : await adminApi.createVariant(t, productId, body);
  if (!result.ok) return failure(result, formData);
  refresh();
  return { success: id ? "Variant saved." : `Variant ${String(body.sku).toUpperCase()} added.`, at: Date.now() };
}

export async function setVariantActiveAction(id: number, active: boolean): Promise<AdminResult> {
  const result = await adminApi.updateVariant(await token(), id, { is_active: active });
  if (!result.ok) return simpleFailure(result);
  refresh();
  return { ok: true };
}

// --- Images --------------------------------------------------------------------------

export async function saveImageAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const productId = Number(formData.get("product_id"));
  const id = Number(formData.get("id")) || null;
  const position = wholeNumber(text(formData, "position"));
  const fields: Record<string, string> = {};
  if (!text(formData, "image_path")) fields.image_path = "Enter an image path.";
  if (!text(formData, "alt_text")) fields.alt_text = "Describe the image for screen readers.";
  if (Number.isNaN(position)) fields.position = "Use a whole number (0 = first).";
  if (Object.keys(fields).length) return invalid(fields, formData);

  const body: Record<string, unknown> = {
    image_path: text(formData, "image_path"),
    alt_text: text(formData, "alt_text"),
    color_name: text(formData, "color_name") || null,
  };
  if (position !== null) body.position = position;
  const t = await token();
  const result = id
    ? await adminApi.updateImage(t, id, body)
    : await adminApi.createImage(t, productId, body);
  if (!result.ok) return failure(result, formData);
  refresh();
  return { success: id ? "Image saved." : "Image added.", at: Date.now() };
}

export async function deleteImageAction(id: number): Promise<AdminResult> {
  const result = await adminApi.deleteImage(await token(), id);
  if (!result.ok) return simpleFailure(result);
  refresh();
  return { ok: true };
}

// --- Inventory -----------------------------------------------------------------------

export async function setStockAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const variantId = Number(formData.get("variant_id"));
  const onHand = wholeNumber(text(formData, "on_hand"));
  if (onHand === null || Number.isNaN(onHand)) {
    return invalid({ on_hand: "Use a whole number of units, e.g. 12." }, formData);
  }
  const result = await adminApi.setOnHand(await token(), variantId, onHand);
  if (!result.ok) return failure(result, formData);
  refresh();
  return {
    success: `Saved: ${result.data.on_hand} on hand, ${result.data.available_quantity} available.`,
    at: Date.now(),
  };
}

// --- Orders --------------------------------------------------------------------------

export async function changeOrderStatusAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const number = text(formData, "order_number");
  const status = text(formData, "status");
  if (!status) return invalid({ status: "Choose the next status." }, formData);
  const result = await adminApi.changeStatus(await token(), number, {
    status,
    note: text(formData, "note") || null,
    internal_note: text(formData, "internal_note") || null,
  });
  if (!result.ok) return failure(result, formData);
  refresh();
  return { success: `Order moved to “${status.replaceAll("_", " ")}”.`, at: Date.now() };
}

export async function changePaymentStatusAction(
  _previous: AdminFormState,
  formData: FormData,
): Promise<AdminFormState> {
  const number = text(formData, "order_number");
  const paymentStatus = text(formData, "payment_status");
  if (!paymentStatus) return invalid({ payment_status: "Choose a payment status." }, formData);
  const result = await adminApi.changePayment(await token(), number, {
    payment_status: paymentStatus,
    note: text(formData, "note") || null,
  });
  if (!result.ok) return failure(result, formData);
  refresh();
  return { success: `Payment recorded as “${paymentStatus}” (manual, demo).`, at: Date.now() };
}

// --- Visual search index -----------------------------------------------------------

export async function rebuildVisualIndexAction(): Promise<AdminFormState> {
  const result = await adminApi.rebuildVisualSearch(await token());
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=%2Fadmin%2Fvisual-search&reason=expired");
    const message =
      result.code === "visual_search_unavailable"
        ? "The vision model isn't available on the server. Run `python -m app.ai.prepare_visual_search` there first."
        : result.code === "index_busy"
          ? "An index build is already running. Try again in a moment."
          : result.message;
    return { error: message, at: Date.now() };
  }
  refresh();
  const r = result.data;
  return {
    success: `Index updated in ${r.seconds}s: ${r.indexed} encoded, ${r.unchanged} unchanged, ${r.removed} removed${r.failed ? `, ${r.failed} failed` : ""}.`,
    at: Date.now(),
  };
}
