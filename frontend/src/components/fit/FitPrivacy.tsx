import { ShieldCheck } from "lucide-react";

// What happens to the photos: shown before anyone uploads anything.
export function FitPrivacy() {
  return (
    <section aria-labelledby="fit-privacy" className="rounded-2xl border border-line bg-white p-5">
      <h2 id="fit-privacy" className="flex items-center gap-2 text-base font-bold text-ink">
        <ShieldCheck className="size-5 text-fit" aria-hidden="true" />
        Your photos and privacy
      </h2>
      <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm text-muted">
        <li>Your photos are analysed once and then discarded. KamerWear does not store them.</li>
        <li>Location and camera details (EXIF) are removed before analysis.</li>
        <li>KamerWear does not train any model on customer photos.</li>
        <li>
          Only the estimated numbers are kept for your review, and nothing becomes your Fit
          Profile until you confirm it.
        </li>
        <li>No face recognition, and no guesses about age, weight, health or identity.</li>
        <li>You can delete your Fit Profile at any time from your account.</li>
      </ul>
    </section>
  );
}
