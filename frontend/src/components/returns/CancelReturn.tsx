"use client";

import { useActionState, useState } from "react";
import { FormMessage } from "@/components/auth/fields";
import { cancelReturnAction, type AfterSalesFormState } from "@/lib/after-sales/actions";

export function CancelReturn({ returnNumber }: { returnNumber: string }) {
  const [state, action, pending] = useActionState<AfterSalesFormState, FormData>(cancelReturnAction, {});
  const [confirming, setConfirming] = useState(false);
  if (!confirming) {
    return (
      <div>
        <FormMessage error={state.error} />
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="inline-flex h-10 items-center rounded-lg border border-line bg-white px-4 text-sm font-semibold text-deal-dark hover:border-deal"
        >
          Cancel return request
        </button>
      </div>
    );
  }
  return (
    <form action={action} aria-labelledby="cancel-return-title" className="rounded-xl border border-deal/30 bg-deal-soft p-4">
      <input type="hidden" name="return_number" value={returnNumber} />
      <p id="cancel-return-title" className="text-sm font-semibold text-deal-dark">
        Cancel this return request?
      </p>
      <p className="mt-1 text-sm text-ink">You can request a new return while the return window is open.</p>
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-10 items-center rounded-lg bg-deal px-4 text-sm font-semibold text-white hover:bg-deal-dark disabled:opacity-70"
        >
          {pending ? "Cancelling…" : "Yes, cancel it"}
        </button>
        <button
          type="button"
          autoFocus
          onClick={() => setConfirming(false)}
          className="inline-flex h-10 items-center rounded-lg px-4 text-sm font-semibold text-ink hover:bg-white"
        >
          Keep the request
        </button>
      </div>
    </form>
  );
}
