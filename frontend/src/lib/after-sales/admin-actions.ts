"use server";

// Admin Server Actions for returns and support. FastAPI checks the ADMIN role,
// the return state machine and the restock rules on every call.

import { refresh } from "next/cache";
import { redirect } from "next/navigation";
import { getAccessToken } from "@/lib/auth/session";
import { returnsApi, supportApi } from "./api";
import type { AfterSalesFormState } from "./actions";

function text(formData: FormData, name: string): string {
  const value = formData.get(name);
  return typeof value === "string" ? value.trim() : "";
}

async function token(): Promise<string> {
  const value = await getAccessToken();
  if (!value) redirect("/login?next=%2Fadmin&reason=expired");
  return value;
}

const DONE: Record<string, string> = {
  approve: "Return approved.",
  reject: "Return rejected.",
  receive: "Return marked received. Restockable items were added back to stock.",
  refund: "Demo/manual refund recorded. No payment provider was contacted.",
};

export async function returnAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const number = text(formData, "return_number");
  const action = text(formData, "action");
  if (!(action in DONE)) return { error: "Unknown action.", at: Date.now() };
  const body: Record<string, unknown> = {
    note: text(formData, "note") || null,
    internal_note: text(formData, "internal_note") || null,
  };
  if (action === "receive") {
    const ids = formData.getAll("item").map(String);
    const missing = ids.find((id) => !text(formData, `restock_${id}`));
    if (missing) {
      return {
        error: "Choose “Restockable” or “Not restockable” for every item.",
        fields: { [`restock_${missing}`]: "Choose one." },
        at: Date.now(),
      };
    }
    body.items = ids.map((id) => ({
      return_item_id: Number(id),
      restock: text(formData, `restock_${id}`) === "yes",
    }));
  }
  if (action === "refund") {
    body.mark_order_payment_refunded = formData.get("mark_order_payment_refunded") === "on";
  }
  const result = await returnsApi.adminAction(await token(), number, action, body);
  if (!result.ok) {
    if (result.status === 401) redirect("/login?next=%2Fadmin&reason=expired");
    return {
      error: result.status === 403 ? "Only administrators can do this." : result.message,
      at: Date.now(),
    };
  }
  refresh();
  return { success: DONE[action], at: Date.now() };
}

export async function adminConversationStatusAction(
  _previous: AfterSalesFormState,
  formData: FormData,
): Promise<AfterSalesFormState> {
  const number = text(formData, "conversation_number");
  const t = await token();
  const result =
    text(formData, "intent") === "reopen"
      ? await supportApi.adminReopen(t, number)
      : await supportApi.adminClose(t, number);
  if (!result.ok) return { error: result.message, at: Date.now() };
  refresh();
  return { at: Date.now() };
}
