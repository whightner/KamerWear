"use client";

import { useActionState, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import { createReturnAction, type AfterSalesFormState } from "@/lib/after-sales/actions";
import { RETURN_REASON_LABELS } from "@/lib/after-sales/labels";
import type { ReturnEligibility, ReturnReason } from "@/lib/after-sales/types";
import { formatXaf } from "@/lib/format";

interface Choice {
  quantity: number;
  reason: ReturnReason | "";
  note: string;
}

const REASONS = Object.entries(RETURN_REASON_LABELS) as [ReturnReason, string][];
const control =
  "h-11 w-full rounded-lg border border-line bg-white px-3 text-sm text-ink outline-none focus:border-ink focus:ring-2 focus:ring-ink/10";

/**
 * Step 1: choose items, quantities and reasons. Step 2: review and submit.
 * The value shown is only a preview; the API recalculates it from the order.
 */
export function ReturnForm({ eligibility }: { eligibility: ReturnEligibility }) {
  const [state, action] = useActionState<AfterSalesFormState, FormData>(createReturnAction, {});
  const items = eligibility.items.filter((item) => item.returnable_quantity > 0);
  const [choices, setChoices] = useState<Record<number, Choice>>(() =>
    Object.fromEntries(items.map((item) => [item.order_item_id, { quantity: 0, reason: "", note: "" }])),
  );
  const [customerNote, setCustomerNote] = useState("");
  const [step, setStep] = useState<"choose" | "review">("choose");
  const [problem, setProblem] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    heading.current?.focus();
  }, [step]);

  // A server error sends the customer back to their choices.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- follow the action result
    if (state.error) setStep("choose");
  }, [state.at, state.error]);

  const selected = items.filter((item) => choices[item.order_item_id].quantity > 0);
  const total = selected.reduce(
    (sum, item) => sum + item.unit_price * choices[item.order_item_id].quantity,
    0,
  );

  function update(id: number, change: Partial<Choice>) {
    setChoices((current) => ({ ...current, [id]: { ...current[id], ...change } }));
  }

  function review() {
    if (selected.length === 0) {
      setProblem("Choose at least one item and a quantity to return.");
      return;
    }
    if (selected.some((item) => !choices[item.order_item_id].reason)) {
      setProblem("Choose a reason for every item you return.");
      return;
    }
    setProblem("");
    setStep("review");
  }

  return (
    <div className="space-y-5">
      <FormMessage error={problem || state.error} />

      {step === "choose" ? (
        <section aria-labelledby="choose-heading">
          <h2 ref={heading} id="choose-heading" tabIndex={-1} className="text-lg font-bold text-ink outline-none">
            1. Choose the items to return
          </h2>
          <ul className="mt-3 space-y-3">
            {items.map((item) => {
              const choice = choices[item.order_item_id];
              const id = item.order_item_id;
              return (
                <li key={id} className="rounded-xl border border-line bg-white p-4">
                  <fieldset>
                    <legend className="sr-only">
                      {item.product_name}
                      {item.size ? `, size ${item.size}` : ""}, {item.color_name}
                    </legend>
                    <div className="flex gap-3">
                      <div className="relative size-16 shrink-0 overflow-hidden rounded-lg bg-cream">
                        {item.image_path && (
                          <Image src={item.image_path} alt="" fill sizes="64px" className="object-cover" />
                        )}
                      </div>
                      <div className="min-w-0 text-sm">
                        <p className="font-semibold text-ink">{item.product_name}</p>
                        <p className="text-xs text-muted">
                          {item.color_name}
                          {item.size && ` · Size ${item.size}`} · {formatXaf(item.unit_price)} each
                        </p>
                        <p className="text-xs text-muted">
                          Bought {item.purchased_quantity}
                          {item.already_returned > 0 && `, ${item.already_returned} already in a return`} · up
                          to {item.returnable_quantity} can be returned
                        </p>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-3 sm:grid-cols-[140px_1fr]">
                      <div>
                        <label htmlFor={`qty-${id}`} className="mb-1.5 block text-sm font-semibold text-ink">
                          Quantity
                        </label>
                        <select
                          id={`qty-${id}`}
                          value={choice.quantity}
                          onChange={(event) => update(id, { quantity: Number(event.target.value) })}
                          className={control}
                        >
                          <option value={0}>Not returning</option>
                          {Array.from({ length: item.returnable_quantity }, (_, i) => i + 1).map((n) => (
                            <option key={n} value={n}>
                              {n}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label htmlFor={`reason-${id}`} className="mb-1.5 block text-sm font-semibold text-ink">
                          Reason
                        </label>
                        <select
                          id={`reason-${id}`}
                          value={choice.reason}
                          disabled={choice.quantity === 0}
                          aria-invalid={
                            choice.quantity > 0 && !choice.reason && problem ? true : undefined
                          }
                          onChange={(event) => update(id, { reason: event.target.value as ReturnReason })}
                          className={`${control} disabled:bg-cream disabled:text-muted`}
                        >
                          <option value="">Choose a reason</option>
                          {REASONS.map(([value, label]) => (
                            <option key={value} value={value}>
                              {label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                    {choice.quantity > 0 && (
                      <div className="mt-3">
                        <label htmlFor={`note-${id}`} className="mb-1.5 block text-sm font-semibold text-ink">
                          Details (optional)
                        </label>
                        <textarea
                          id={`note-${id}`}
                          value={choice.note}
                          maxLength={500}
                          rows={2}
                          onChange={(event) => update(id, { note: event.target.value })}
                          placeholder="e.g. The seam on the left sleeve is torn."
                          className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
                        />
                      </div>
                    )}
                  </fieldset>
                </li>
              );
            })}
          </ul>
          <div className="mt-4">
            <label htmlFor="customer-note" className="mb-1.5 block text-sm font-semibold text-ink">
              Anything else we should know? (optional)
            </label>
            <textarea
              id="customer-note"
              value={customerNote}
              maxLength={1000}
              rows={3}
              onChange={(event) => setCustomerNote(event.target.value)}
              className="w-full rounded-lg border border-line bg-white px-3 py-2 text-sm text-ink outline-none focus:border-ink focus:ring-2 focus:ring-ink/10"
            />
          </div>
          <p className="mt-3 text-xs text-muted">
            Photo evidence isn&apos;t supported yet; describe the issue in the details instead.
          </p>
          <div className="mt-5 flex justify-end">
            <button
              type="button"
              onClick={review}
              className="inline-flex h-11 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
            >
              Review return
            </button>
          </div>
        </section>
      ) : (
        <form action={action} aria-labelledby="review-heading" className="rounded-xl border border-line bg-white p-5">
          <h2 ref={heading} id="review-heading" tabIndex={-1} className="text-lg font-bold text-ink outline-none">
            2. Review and submit
          </h2>
          <input type="hidden" name="order_number" value={eligibility.order_number} />
          <input type="hidden" name="customer_note" value={customerNote} />
          <ul className="mt-3 divide-y divide-line text-sm">
            {selected.map((item) => {
              const choice = choices[item.order_item_id];
              const id = item.order_item_id;
              return (
                <li key={id} className="py-2">
                  <input type="hidden" name="item" value={id} />
                  <input type="hidden" name={`quantity_${id}`} value={choice.quantity} />
                  <input type="hidden" name={`reason_${id}`} value={choice.reason} />
                  <input type="hidden" name={`note_${id}`} value={choice.note} />
                  <p className="font-semibold text-ink">
                    {choice.quantity} × {item.product_name}
                    {item.size && ` (${item.size})`}
                  </p>
                  <p className="text-xs text-muted">
                    {RETURN_REASON_LABELS[choice.reason as ReturnReason]}
                    {choice.note && ` · “${choice.note}”`}
                  </p>
                </li>
              );
            })}
          </ul>
          <p className="mt-3 flex justify-between border-t border-line pt-3 text-sm">
            <span className="text-muted">Merchandise value (at the price you paid)</span>
            <span className="font-bold text-ink">{formatXaf(total)}</span>
          </p>
          <p className="mt-1 text-xs text-muted">
            Delivery fees aren&apos;t included. Refunds are recorded manually by our team after we
            receive the items (demo: no money moves).
          </p>
          <div className="mt-5 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button
              type="button"
              onClick={() => setStep("choose")}
              className="inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-semibold text-muted hover:text-ink"
            >
              Change items
            </button>
            <div className="sm:w-60">
              <SubmitButton pendingLabel="Submitting…">Submit return request</SubmitButton>
            </div>
          </div>
        </form>
      )}
    </div>
  );
}
