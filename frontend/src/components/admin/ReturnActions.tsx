"use client";

import { useActionState } from "react";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import { returnAction } from "@/lib/after-sales/admin-actions";
import type { AfterSalesFormState } from "@/lib/after-sales/actions";
import type { AdminReturnDetail } from "@/lib/after-sales/types";
import { TextAreaField } from "./fields";

function Notes({ notePlaceholder }: { notePlaceholder: string }) {
  return (
    <>
      <TextAreaField
        label="Note for the customer (optional)"
        name="note"
        maxLength={500}
        rows={2}
        placeholder={notePlaceholder}
        hint="Shown on the customer's return page."
      />
      <TextAreaField
        label="Internal note (optional)"
        name="internal_note"
        maxLength={500}
        rows={2}
        hint="Staff only — never shown to the customer."
      />
    </>
  );
}

/** The next step(s) the return state machine allows. */
export function ReturnActions({ detail }: { detail: AdminReturnDetail }) {
  const [state, action] = useActionState<AfterSalesFormState, FormData>(returnAction, {});
  const allowed = detail.allowed_actions;
  const hidden = <input type="hidden" name="return_number" value={detail.return_number} />;

  if (allowed.length === 0) {
    return (
      <>
        <FormMessage success={state.success} />
        <p className="mt-2 text-sm text-muted">This return is closed: no further steps.</p>
      </>
    );
  }

  return (
    <div className="space-y-4" key={allowed.join()}>
      <FormMessage error={state.error} success={state.success} />

      {allowed.includes("approve") && (
        <form action={action} className="space-y-3">
          {hidden}
          <h3 className="text-sm font-bold text-ink">Approve or reject</h3>
          <Notes notePlaceholder="Approved: please bring the items to our Akwa shop." />
          <div className="grid gap-2 sm:grid-cols-2">
            <button
              type="submit"
              name="action"
              value="approve"
              className="flex h-11 items-center justify-center rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
            >
              Approve return
            </button>
            <button
              type="submit"
              name="action"
              value="reject"
              className="flex h-11 items-center justify-center rounded-lg border border-deal/40 bg-white px-5 text-sm font-semibold text-deal-dark hover:bg-deal-soft"
            >
              Reject return
            </button>
          </div>
        </form>
      )}

      {allowed.includes("receive") && (
        <form action={action} className="space-y-3">
          {hidden}
          <input type="hidden" name="action" value="receive" />
          <h3 className="text-sm font-bold text-ink">Mark items received</h3>
          <p className="text-xs text-muted">
            Choose for each item whether it can be sold again. Restockable units are added to
            on-hand stock once; damaged items are not.
          </p>
          {detail.items.map((item) => (
            <fieldset key={item.id} className="rounded-lg border border-line p-3">
              <input type="hidden" name="item" value={item.id} />
              <legend className="px-1 text-sm font-semibold text-ink">
                {item.quantity} × {item.product_name}
                {item.size && ` (${item.size})`} · {item.sku}
              </legend>
              <div className="flex flex-wrap gap-4 text-sm">
                <label className="flex items-center gap-2">
                  <input type="radio" name={`restock_${item.id}`} value="yes" required />
                  Restockable
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="radio"
                    name={`restock_${item.id}`}
                    value="no"
                    defaultChecked={item.reason === "damaged"}
                  />
                  Not restockable
                </label>
              </div>
              {state.fields?.[`restock_${item.id}`] && (
                <p className="mt-1 text-xs font-medium text-deal-dark">{state.fields[`restock_${item.id}`]}</p>
              )}
            </fieldset>
          ))}
          <Notes notePlaceholder="We received your parcel." />
          <SubmitButton pendingLabel="Saving…">Mark received</SubmitButton>
        </form>
      )}

      {allowed.includes("refund") && (
        <form action={action} className="space-y-3">
          {hidden}
          <input type="hidden" name="action" value="refund" />
          <h3 className="text-sm font-bold text-ink">Record the refund</h3>
          <p className="rounded-lg border border-gold/40 bg-gold-soft px-3 py-2 text-xs font-medium text-ink">
            Demo/manual record only. No Mobile Money, Orange Money or card refund is executed and
            no money moves. Amount: merchandise value of this return.
          </p>
          {detail.can_mark_order_refunded && (
            <label className="flex items-start gap-2 text-sm text-ink">
              <input type="checkbox" name="mark_order_payment_refunded" className="mt-1" />
              Also mark the order payment as refunded (every item of the order has been returned).
            </label>
          )}
          <Notes notePlaceholder="Refund sent manually." />
          <SubmitButton pendingLabel="Saving…">Record demo refund</SubmitButton>
        </form>
      )}
    </div>
  );
}
