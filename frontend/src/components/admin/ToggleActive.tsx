"use client";

import { useState, useTransition } from "react";
import type { AdminResult } from "@/lib/admin/actions";

/** Activate/deactivate button with a short confirmation of the outcome. */
export function ToggleActive({
  active,
  action,
  activateLabel = "Activate",
  deactivateLabel = "Deactivate",
  name,
}: {
  active: boolean;
  action: (next: boolean) => Promise<AdminResult>;
  activateLabel?: string;
  deactivateLabel?: string;
  /** What is toggled, for screen readers, e.g. "Urban Runner 02". */
  name: string;
}) {
  const [pending, start] = useTransition();
  const [error, setError] = useState("");
  return (
    <span className="inline-flex flex-col items-start gap-1">
      <button
        type="button"
        disabled={pending}
        aria-label={`${active ? deactivateLabel : activateLabel} ${name}`}
        onClick={() =>
          start(async () => {
            setError("");
            const result = await action(!active);
            if (!result.ok) setError(result.message);
          })
        }
        className={`h-8 rounded-md px-3 text-xs font-semibold disabled:opacity-60 ${
          active ? "border border-line text-ink hover:bg-cream" : "bg-fit text-white hover:bg-fit-dark"
        }`}
      >
        {pending ? "Saving…" : active ? deactivateLabel : activateLabel}
      </button>
      {error && (
        <span role="alert" className="text-xs font-medium text-deal-dark">
          {error}
        </span>
      )}
    </span>
  );
}
