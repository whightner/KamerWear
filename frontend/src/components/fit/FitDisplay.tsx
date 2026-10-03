import { CONFIDENCE_TEXT, type FitConfidence, type FitMeasurements } from "@/lib/fit/types";

// Read-only pieces shared by the review step and the account page.

const ROWS: { key: keyof FitMeasurements; label: string }[] = [
  { key: "chest_cm", label: "Chest" },
  { key: "waist_cm", label: "Waist" },
  { key: "hip_cm", label: "Hips" },
  { key: "inseam_cm", label: "Inseam" },
  { key: "shoulder_width_cm", label: "Between shoulder joints" },
];

const BADGE: Record<FitConfidence, string> = {
  high: "bg-fit text-white",
  medium: "bg-gold-soft text-ink ring-1 ring-gold",
  low: "bg-deal-soft text-deal-dark ring-1 ring-deal/40",
};

export function ConfidenceBadge({ confidence }: { confidence: FitConfidence }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold ${BADGE[confidence]}`}>
      {CONFIDENCE_TEXT[confidence]}
    </span>
  );
}

/** Whole centimetres with "about": one decimal would suggest false precision. */
export function MeasurementList({ measurements }: { measurements: FitMeasurements }) {
  return (
    <dl className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-5">
      {ROWS.map(({ key, label }) => {
        const value = measurements[key];
        return (
          <div key={key} className="min-w-0 rounded-lg border border-line px-3 py-2">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="text-sm font-semibold text-ink">
              {value === null ? (
                <span className="font-normal text-muted">Not estimated</span>
              ) : (
                <>
                  <span className="sr-only">about </span>
                  <span aria-hidden="true">≈ </span>
                  {Math.round(value)} cm
                </>
              )}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
