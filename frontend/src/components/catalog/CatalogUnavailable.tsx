"use client";

import { useTransition } from "react";
import { useRouter } from "next/navigation";
import { RefreshCw } from "lucide-react";

// Shown when the catalog API can't be reached. Deliberately different from
// "no products match", and never replaced by stale or mock products.
export function CatalogUnavailable({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();

  return (
    <div
      role="alert"
      className={`rounded-xl border border-line bg-white text-center ${compact ? "px-6 py-10" : "px-6 py-16"}`}
    >
      <p className="text-lg font-bold text-ink">
        We couldn&apos;t load the catalog right now.
      </p>
      <p className="mt-1 text-sm text-muted">Please try again in a moment.</p>
      <button
        type="button"
        onClick={() => startTransition(() => router.refresh())}
        disabled={pending}
        className="mt-5 inline-flex h-10 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white disabled:opacity-60"
      >
        <RefreshCw
          className={`size-4 ${pending ? "animate-spin" : ""}`}
          aria-hidden="true"
        />
        {pending ? "Retrying…" : "Try again"}
      </button>
    </div>
  );
}
