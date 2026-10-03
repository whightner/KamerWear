"use client";

import { useActionState } from "react";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import { rebuildVisualIndexAction, type AdminFormState } from "@/lib/admin/actions";

export function RebuildIndexButton() {
  const [state, formAction] = useActionState<AdminFormState, FormData>(rebuildVisualIndexAction, {});
  return (
    <form action={formAction} className="space-y-3">
      <FormMessage error={state.error} success={state.success} />
      <div className="sm:w-60">
        <SubmitButton pendingLabel="Indexing images…">Update visual index</SubmitButton>
      </div>
      <p className="text-xs text-muted">
        Encodes new or changed product photos with the vision model. Takes a few seconds for the
        demo catalog; only one update runs at a time.
      </p>
    </form>
  );
}
