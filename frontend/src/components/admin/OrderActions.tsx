"use client";

import { useActionState } from "react";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import {
  changeOrderStatusAction,
  changePaymentStatusAction,
  type AdminFormState,
} from "@/lib/admin/actions";
import { ORDER_STATUS_LABELS } from "@/lib/commerce/labels";
import type { OrderStatus, PaymentStatus } from "@/lib/commerce/types";
import { SelectField, TextAreaField } from "./fields";

export function OrderStatusForm({
  orderNumber,
  allowed,
}: {
  orderNumber: string;
  allowed: OrderStatus[];
}) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(changeOrderStatusAction, {});
  if (allowed.length === 0) {
    return (
      <>
        <FormMessage success={state.success} />
        <p className="mt-2 text-sm text-muted">This order is closed: no further status changes.</p>
      </>
    );
  }
  return (
    <form action={formAction} noValidate className="space-y-3" key={allowed.join()}>
      <input type="hidden" name="order_number" value={orderNumber} />
      <FormMessage error={state.error} success={state.success} />
      <SelectField label="Next status" name="status" defaultValue={allowed[0]} error={state.fields?.status}>
        {allowed.map((status) => (
          <option key={status} value={status}>
            {ORDER_STATUS_LABELS[status]}
          </option>
        ))}
      </SelectField>
      <TextAreaField
        label="Note for the customer (optional)"
        name="note"
        maxLength={255}
        rows={2}
        placeholder="Packed and ready for pickup."
        hint="Shown on the customer's order page."
        error={state.fields?.note}
      />
      <TextAreaField
        label="Internal note (optional)"
        name="internal_note"
        maxLength={500}
        rows={2}
        placeholder="Courier assigned: Paul, Akwa route."
        hint="Staff only — never shown to the customer."
        error={state.fields?.internal_note}
      />
      <p className="text-xs text-muted">
        Cancelling releases reserved stock. Delivering removes the units from stock. Both happen once.
      </p>
      <SubmitButton pendingLabel="Updating…">Update status</SubmitButton>
    </form>
  );
}

export function PaymentStatusForm({
  orderNumber,
  allowed,
}: {
  orderNumber: string;
  allowed: PaymentStatus[];
}) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(changePaymentStatusAction, {});
  return (
    <div>
      <p className="mb-3 rounded-lg border border-gold/40 bg-gold-soft px-3 py-2 text-xs font-medium text-ink">
        Demo/manual payment state. No payment provider confirmed anything and no money moves.
      </p>
      {allowed.length === 0 ? (
        <>
          <FormMessage success={state.success} />
          <p className="mt-2 text-sm text-muted">No further payment changes are possible.</p>
        </>
      ) : (
        <form action={formAction} noValidate className="space-y-3" key={allowed.join()}>
          <input type="hidden" name="order_number" value={orderNumber} />
          <FormMessage error={state.error} success={state.success} />
          <SelectField label="Record payment as" name="payment_status" defaultValue={allowed[0]} error={state.fields?.payment_status}>
            {allowed.map((status) => (
              <option key={status} value={status}>
                {status.charAt(0).toUpperCase() + status.slice(1)}
              </option>
            ))}
          </SelectField>
          <TextAreaField label="Note (optional, staff only)" name="note" maxLength={500} rows={2} placeholder="Cash collected by the courier." error={state.fields?.note} />
          <SubmitButton pendingLabel="Saving…">Record payment status</SubmitButton>
        </form>
      )}
    </div>
  );
}
