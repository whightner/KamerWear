"use client";

import { useActionState, useState } from "react";
import { AlertTriangle, Info } from "lucide-react";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import { saveFitProfile, type FitFormState } from "@/lib/fit/actions";
import type { FitEstimate, FitPreference, FitProfile } from "@/lib/fit/types";
import { ConfidenceBadge, MeasurementList } from "./FitDisplay";
import { PreferenceField, SizeSelects } from "./SizeFields";

interface FitReviewProps {
  estimate: FitEstimate;
  initialPreference: FitPreference;
  shoe: string;
  /** The saved profile, shown for comparison when rescanning. */
  savedProfile: FitProfile | null;
  onRetake: () => void;
}

/**
 * The customer checks the estimate, corrects anything and confirms. Nothing
 * is saved before "Save my Fit Profile".
 */
export function FitReview({ estimate, initialPreference, shoe, savedProfile, onRetake }: FitReviewProps) {
  const [state, action] = useActionState<FitFormState, FormData>(saveFitProfile, {});
  const [preference, setPreference] = useState(initialPreference);
  const suggested = estimate.suggested_by_preference[preference];
  // Sizes follow the suggestion until the customer picks one themselves.
  const [top, setTop] = useState<string | null>(null);
  const [bottom, setBottom] = useState<string | null>(null);
  const [shoeSize, setShoeSize] = useState(shoe);
  const topValue = top ?? suggested.top ?? "";
  const bottomValue = bottom ?? suggested.bottom ?? "";

  const suggestionHint = (value: string | null, saved: string | null | undefined) =>
    [value ? `Suggested: ${value}` : "No suggestion: please choose", saved ? `saved: ${saved}` : null]
      .filter(Boolean)
      .join(" · ");

  return (
    <div className="mt-4 space-y-6">
      <section aria-labelledby="confidence-heading" className="rounded-xl bg-cream p-4">
        <div className="flex flex-wrap items-center gap-3">
          <h3 id="confidence-heading" className="text-sm font-bold text-ink">
            Estimate confidence
          </h3>
          <ConfidenceBadge confidence={estimate.confidence} />
        </div>
        <p className="mt-2 text-xs text-muted">
          Confidence shows how well your photos supported the estimate. It is not an accuracy
          percentage, and these are estimates, not tailor measurements.
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
          {estimate.confidence_factors.map((factor) => (
            <li key={factor}>{factor}</li>
          ))}
        </ul>
      </section>

      {estimate.warnings.length > 0 && (
        <section
          aria-labelledby="warnings-heading"
          className="rounded-xl border border-gold/50 bg-gold-soft p-4"
        >
          <h3 id="warnings-heading" className="flex items-center gap-2 text-sm font-bold text-ink">
            <AlertTriangle className="size-4" aria-hidden="true" />
            Tips to improve your result
          </h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-ink">
            {estimate.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={onRetake}
            className="mt-3 text-sm font-semibold text-ink underline underline-offset-2"
          >
            Retake photos
          </button>
        </section>
      )}

      <section aria-labelledby="measurements-heading">
        <h3 id="measurements-heading" className="text-sm font-bold text-ink">
          Estimated body dimensions
        </h3>
        <p className="mt-1 text-xs text-muted">
          Approximate, from your photos and your height of {estimate.height_cm} cm. Used only to
          suggest sizes.
        </p>
        <MeasurementList measurements={estimate.measurements} />
      </section>

      <form action={action} className="space-y-5 border-t border-line pt-5">
        <input type="hidden" name="estimate_id" value={estimate.estimate_id} />
        <input type="hidden" name="height_cm" value={estimate.height_cm} />
        <div>
          <h3 className="text-sm font-bold text-ink">Your sizes</h3>
          <p className="mt-1 text-xs text-muted">
            Check the suggested sizes and change anything that doesn&apos;t match what you usually
            wear. What you save here is what KamerWear will recommend.
          </p>
        </div>
        <PreferenceField value={preference} onChange={setPreference} />
        {estimate.size_notes.length > 0 && preference === estimate.fit_preference && (
          <p className="flex gap-2 text-xs text-muted">
            <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            {estimate.size_notes.join(" ")}
          </p>
        )}
        <SizeSelects
          top={topValue}
          bottom={bottomValue}
          shoe={shoeSize}
          onTop={setTop}
          onBottom={setBottom}
          onShoe={setShoeSize}
          errors={state.fields}
          hints={{
            top: suggestionHint(suggested.top, savedProfile?.top_size),
            bottom: suggestionHint(suggested.bottom, savedProfile?.bottom_size),
            shoe: "Confirmed shoe size, entered by you (not estimated).",
          }}
        />
        <FormMessage error={state.error} />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <button
            type="button"
            onClick={onRetake}
            className="inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-semibold text-muted hover:text-ink"
          >
            Retake photos
          </button>
          <div className="sm:w-64">
            <SubmitButton pendingLabel="Saving…">Save my Fit Profile</SubmitButton>
          </div>
        </div>
      </form>
    </div>
  );
}
