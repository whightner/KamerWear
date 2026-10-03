"use client";

import Link from "next/link";
import { Ruler } from "lucide-react";
import type { ProductFitState } from "@/lib/fit/types";

interface SmartFitBlockProps {
  fit: ProductFitState;
  /** Size currently selected in the size picker. */
  selectedSize?: string;
  /** Whether this size can be selected (exists and is in stock for the colour). */
  canSelect: (size: string) => boolean;
  /** Only selects the size: never adds to the cart. */
  onSelectSize: (size: string) => void;
  productPath: string;
}

const KIND_LABEL = { top: "size", bottom: "trouser size", shoe: "shoe size" } as const;

/**
 * The customer's recommended size from their confirmed Fit Profile. Hidden for
 * products Smart Fit doesn't support. A Smart Fit problem never blocks buying.
 */
export function SmartFitBlock({
  fit,
  selectedSize,
  canSelect,
  onSelectSize,
  productPath,
}: SmartFitBlockProps) {
  if (fit.status === "unsupported") return null;

  let body: React.ReactNode;
  if (fit.status === "signed_out") {
    body = (
      <>
        <p className="text-sm text-ink">Log in to see the size recommended for you.</p>
        <Links
          primary={{ href: `/login?next=${encodeURIComponent(productPath)}`, label: "Log in" }}
        />
      </>
    );
  } else if (fit.status === "error") {
    body = (
      <p className="text-sm text-ink">
        Your recommendation isn&apos;t available right now. You can still choose a size below.
      </p>
    );
  } else if (fit.status === "no_profile") {
    body = (
      <>
        <p className="text-sm text-ink">Create your Fit Profile to see your recommended size.</p>
        <Links primary={{ href: "/fit", label: "Create My Fit Profile" }} />
      </>
    );
  } else if (fit.status === "missing_size") {
    body = (
      <>
        <p className="text-sm text-ink">{fit.message}</p>
        <Links primary={{ href: "/account/fit-profile", label: "Update my Fit Profile" }} />
      </>
    );
  } else {
    const label = fit.size_label ?? fit.size ?? "";
    const nearest = fit.nearest_available;
    const nearestLabel = nearest && fit.kind === "shoe" ? `EU ${nearest}` : nearest;
    const isSelected = selectedSize === fit.size;
    body = (
      <>
        <p className="text-sm text-ink">
          {fit.kind ? `Recommended ${KIND_LABEL[fit.kind]} for you` : "Recommended for you"}:{" "}
          <strong className="text-base">{label}</strong>
        </p>
        {fit.status !== "recommended" && fit.message && (
          <p className="mt-1 text-sm font-medium text-deal-dark">{fit.message}</p>
        )}
        <p className="mt-0.5 text-xs text-muted">
          From the {fit.kind === "shoe" ? "shoe size you entered" : "sizes you confirmed"} in your
          Fit Profile.
        </p>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
          {fit.status === "recommended" && fit.size && canSelect(fit.size) && (
            <button
              type="button"
              onClick={() => onSelectSize(fit.size!)}
              aria-pressed={isSelected}
              disabled={isSelected}
              className="text-fit-dark underline underline-offset-2 disabled:no-underline disabled:opacity-80"
            >
              {isSelected ? `${label} selected` : `Select recommended size ${label}`}
            </button>
          )}
          {fit.status !== "recommended" && nearest && canSelect(nearest) && (
            <button
              type="button"
              onClick={() => onSelectSize(nearest)}
              aria-pressed={selectedSize === nearest}
              className="text-fit-dark underline underline-offset-2"
            >
              Select {nearestLabel} instead
            </button>
          )}
          <Link href="/account/fit-profile" className="text-fit-dark underline underline-offset-2">
            My Fit Profile
          </Link>
        </div>
      </>
    );
  }

  return (
    <section aria-labelledby="smart-fit-heading" className="rounded-xl border border-fit/25 bg-fit-soft p-4">
      <h2 id="smart-fit-heading" className="flex items-center gap-1.5 text-sm font-bold text-fit-dark">
        <Ruler className="size-4" aria-hidden="true" />
        Smart Fit
      </h2>
      <div className="mt-1.5">{body}</div>
    </section>
  );
}

function Links({ primary }: { primary: { href: string; label: string } }) {
  return (
    <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
      <Link href={primary.href} className="text-fit-dark underline underline-offset-2">
        {primary.label}
      </Link>
      {primary.href !== "/fit" && (
        <Link href="/fit" className="text-fit-dark underline underline-offset-2">
          How Smart Fit works
        </Link>
      )}
    </div>
  );
}
