"use client";

import { useActionState } from "react";
import { setConversationStatusAction, type AfterSalesFormState } from "@/lib/after-sales/actions";
import { adminConversationStatusAction } from "@/lib/after-sales/admin-actions";
import type { ConversationStatus } from "@/lib/after-sales/types";

/** Close or reopen a conversation (customer or admin side). */
export function ConversationStatusForm({
  number,
  status,
  admin = false,
}: {
  number: string;
  status: ConversationStatus;
  admin?: boolean;
}) {
  const [state, action, pending] = useActionState<AfterSalesFormState, FormData>(
    admin ? adminConversationStatusAction : setConversationStatusAction,
    {},
  );
  const reopen = status === "closed";
  return (
    <form action={action} className="flex items-center gap-2">
      <input type="hidden" name="conversation_number" value={number} />
      <input type="hidden" name="intent" value={reopen ? "reopen" : "close"} />
      <button
        type="submit"
        disabled={pending}
        className="inline-flex h-10 items-center rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-ink disabled:opacity-60"
      >
        {reopen ? "Reopen conversation" : "Close conversation"}
      </button>
      {state.error && (
        <span role="alert" className="text-xs text-deal-dark">
          {state.error}
        </span>
      )}
    </form>
  );
}
