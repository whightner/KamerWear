"use client";

import { useState } from "react";
import Link from "next/link";
import { Ruler } from "lucide-react";

interface SmartFitBlockProps {
  isShoe: boolean;
  demoSize?: string;
  /** Selecting the recommended size is only offered when it is available. */
  canSelect: boolean;
  onSelectSize: (size: string) => void;
}

// No Fit Profile exists yet, so this shows the "create a profile" state and
// an optional, clearly labelled demo recommendation.
export function SmartFitBlock({
  isShoe,
  demoSize,
  canSelect,
  onSelectSize,
}: SmartFitBlockProps) {
  const [showDemo, setShowDemo] = useState(false);
  const sizeLabel = isShoe ? `EU ${demoSize}` : demoSize;

  return (
    <section
      aria-labelledby="smart-fit-heading"
      className="rounded-xl border border-fit/25 bg-fit-soft p-4"
    >
      <h2
        id="smart-fit-heading"
        className="flex items-center gap-1.5 text-sm font-bold text-fit-dark"
      >
        <Ruler className="size-4" aria-hidden="true" />
        Smart Fit recommendation
      </h2>

      {showDemo && demoSize ? (
        <div className="mt-2">
          <p className="text-sm text-ink">
            {isShoe ? "Recommended shoe size" : "Recommended size"}:{" "}
            <strong>{sizeLabel}</strong>
          </p>
          <p className="mt-0.5 text-xs text-muted">
            Estimated from a demo Fit Profile, not your measurements. Confirm
            before buying.
          </p>
          {canSelect && (
            <button
              type="button"
              onClick={() => onSelectSize(demoSize)}
              className="mt-2 text-xs font-semibold text-fit-dark underline underline-offset-2"
            >
              Select {sizeLabel}
            </button>
          )}
        </div>
      ) : (
        <div className="mt-1.5">
          <p className="text-sm text-ink">
            Create a Fit Profile to get a personal recommendation.
          </p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs font-semibold">
            <Link
              href="/#smart-fit"
              className="text-fit-dark underline underline-offset-2"
            >
              How Smart Fit works
            </Link>
            {demoSize && (
              <button
                type="button"
                onClick={() => setShowDemo(true)}
                className="text-fit-dark underline underline-offset-2"
              >
                Preview a demo recommendation
              </button>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
