"use client";

import { useActionState } from "react";
import { setStockAction, type AdminFormState } from "@/lib/admin/actions";

/** Inline "on hand" editor. Reserved units are shown, never edited. */
export function StockForm({
  variantId,
  onHand,
  reserved,
  label,
}: {
  variantId: number;
  onHand: number;
  reserved: number;
  /** Accessible name of the input, e.g. "On hand for UR02-BLACK-43". */
  label: string;
}) {
  const [state, formAction, pending] = useActionState<AdminFormState, FormData>(setStockAction, {});
  const inputId = `stock-${variantId}`;
  const messageId = `${inputId}-message`;
  return (
    <form action={formAction} className="flex flex-col gap-1">
      <input type="hidden" name="variant_id" value={variantId} />
      <div className="flex items-center gap-2">
        <label htmlFor={inputId} className="sr-only">
          {label}
        </label>
        <input
          key={`${onHand}-${state.at ?? 0}`}
          id={inputId}
          name="on_hand"
          inputMode="numeric"
          defaultValue={state.error ? (state.values?.on_hand ?? String(onHand)) : String(onHand)}
          min={reserved}
          aria-invalid={state.error ? true : undefined}
          aria-describedby={state.error || state.success ? messageId : undefined}
          className={`h-9 w-20 rounded-md border bg-white px-2 text-right text-sm ${state.error ? "border-deal" : "border-line"}`}
        />
        <button
          type="submit"
          disabled={pending}
          className="h-9 rounded-md border border-ink px-3 text-xs font-semibold text-ink hover:bg-ink hover:text-white disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save"}
        </button>
      </div>
      <p id={messageId} aria-live="polite" className={`max-w-56 text-xs ${state.error ? "font-medium text-deal-dark" : "text-fit-dark"}`}>
        {state.error ? (state.fields?.on_hand ?? state.error) : state.success}
      </p>
    </form>
  );
}
