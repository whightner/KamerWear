"use server";

// Customer Server Actions for returns and support. FastAPI validates
// ownership, eligibility, quantities and message rules; nothing about the
// owner, prices or totals is sent from here.

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import { getAccessToken } from "@/lib/auth/session";
import { returnsApi, supportApi } from "./api";

export interface AfterSalesFormState {
  error?: string;
  success?: string;
  fields?: Record<string, string>;
  at?: number;
}

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

async function token(next: string): Promise<string> {
  const value = await getAccessToken();
  if (!value) redirect(`/login?next=${encodeURIComponent(next)}&reason=expired`);
  return value;
}

export async function createReturnAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const orderNumber = text(formData, "order_number");
  const page = `/orders/${orderNumber}/return`;
  const items = formData
    .getAll("item")
    .map(String)
    .map((id) => ({
      order_item_id: Number(id),
      quantity: Number(text(formData, `quantity_${id}`)),
      reason: text(formData, `reason_${id}`),
      note: text(formData, `note_${id}`) || null,
    }))
    .filter((item) => item.quantity > 0);
  if (items.length === 0) {
    return { error: "Choose at least one item and a quantity to return.", at: Date.now() };
  }
  const missingReason = items.find((item) => !item.reason);
  if (missingReason) {
    return {
      error: "Choose a reason for every item you return.",
      fields: { [`reason_${missingReason.order_item_id}`]: "Choose a reason." },
      at: Date.now(),
    };
  }
  const result = await returnsApi.create(await token(page), {
    order_number: orderNumber,
    items,
    customer_note: text(formData, "customer_note") || null,
  });
  if (!result.ok) {
    if (result.status === 401) redirect(`/login?next=${encodeURIComponent(page)}&reason=expired`);
    return {
      error:
        result.code === "validation_error"
          ? "Please check the quantities, reasons and notes."
          : result.message,
      at: Date.now(),
    };
  }
  redirect(`/returns/${result.data.return_number}?created=1`);
}

export async function cancelReturnAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const number = text(formData, "return_number");
  const result = await returnsApi.cancel(await token(`/returns/${number}`), number, null);
  if (!result.ok) {
    if (result.status === 401) redirect(`/login?next=/returns/${number}&reason=expired`);
    return { error: result.message, at: Date.now() };
  }
  redirect(`/returns/${number}?cancelled=1`);
}

export async function startConversationAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const subject = text(formData, "subject");
  const message = text(formData, "message");
  const fields: Record<string, string> = {};
  if (!subject) fields.subject = "Choose a subject.";
  if (!message) fields.message = "Please write a message.";
  if (Object.keys(fields).length) {
    return { error: "Please check the highlighted fields.", fields, at: Date.now() };
  }
  const result = await supportApi.create(await token("/support/new"), {
    subject,
    message,
    order_number: text(formData, "order_number") || null,
    return_number: text(formData, "return_number") || null,
  });
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=/support/new&reason=expired");
    const field = result.code.startsWith("message_") ? "message" : undefined;
    return {
      error: result.code === "validation_error" ? "Please check your message." : result.message,
      fields: field ? { [field]: result.message } : result.fields,
      at: Date.now(),
    };
  }
  redirect(`/support/${result.data.conversation_number}`);
}

export async function setConversationStatusAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const number = text(formData, "conversation_number");
  const t = await token(`/support/${number}`);
  const result =
    text(formData, "intent") === "reopen"
      ? await supportApi.reopen(t, number)
      : await supportApi.close(t, number);
  if (!result.ok) return { error: result.message, at: Date.now() };
  refresh();
  return { at: Date.now() };
}
