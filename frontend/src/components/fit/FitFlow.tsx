"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, ScanLine } from "lucide-react";
import { TextField } from "@/components/auth/fields";
import { ensureFitSession } from "@/lib/fit/actions";
import {
  HEIGHT_MAX,
  HEIGHT_MIN,
  SHOE_SIZES,
  type FitApiError,
  type FitEstimate,
  type FitPreference,
  type FitProfile,
} from "@/lib/fit/types";
import { SelectField } from "@/components/admin/fields";
import { FitReview } from "./FitReview";
import { PhotoPicker } from "./PhotoPicker";
import { PreferenceField } from "./SizeFields";

type Step = "details" | "front" | "side" | "analysing" | "review";

const STEPS: { key: Step; label: string }[] = [
  { key: "details", label: "Height" },
  { key: "front", label: "Front photo" },
  { key: "side", label: "Side photo" },
  { key: "review", label: "Review" },
];

const GENERAL_ERRORS: Record<string, string> = {
  too_many_fit_estimates:
    "You've asked for many estimates in a short time. Please wait a few minutes and try again.",
  fit_service_unavailable:
    "Photo sizing is unavailable right now. You can still enter your sizes yourself.",
  unavailable: "We couldn't reach KamerWear right now. Please check your connection and try again.",
};

const FRONT_TIPS = [
  "Your whole body is in the photo, from the top of your head to your feet.",
  "Stand straight and face the camera, feet slightly apart.",
  "Hold your arms slightly away from your body.",
  "Wear everyday clothes that follow your shape; take off a big coat or bag.",
  "Use good light and keep the camera level, about waist height.",
  "Only you in the photo. Ask someone to take it, or prop the phone up and use the timer.",
];

const SIDE_TIPS = [
  "Turn 90 degrees so your side faces the camera, whole body visible.",
  "Stand straight with your arms relaxed down by your sides (not crossed, hands out of pockets).",
  "Same place, light and camera position as the front photo.",
];

interface FitFlowProps {
  /** The current Fit Profile, if any: prefills height, preference and shoe size. */
  profile: FitProfile | null;
}

export function FitFlow({ profile }: FitFlowProps) {
  const router = useRouter();
  const [step, setStep] = useState<Step>("details");
  const [height, setHeight] = useState(profile ? String(profile.height_cm) : "");
  const [heightError, setHeightError] = useState("");
  const [preference, setPreference] = useState<FitPreference>(profile?.fit_preference ?? "regular");
  const [shoe, setShoe] = useState(profile?.shoe_size_eu ? String(profile.shoe_size_eu) : "");
  const [front, setFront] = useState<File | null>(null);
  const [side, setSide] = useState<File | null>(null);
  const [photoError, setPhotoError] = useState<{ front?: string; side?: string }>({});
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [estimate, setEstimate] = useState<FitEstimate | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const firstRender = useRef(true);

  // Move focus to the new step's heading so keyboard and screen-reader users
  // start at the top of each step.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    heading.current?.focus();
  }, [step]);

  function submitDetails(event: FormEvent) {
    event.preventDefault();
    const value = Number(height);
    if (!Number.isInteger(value) || value < HEIGHT_MIN || value > HEIGHT_MAX) {
      setHeightError(`Enter your height in whole centimetres, between ${HEIGHT_MIN} and ${HEIGHT_MAX}.`);
      return;
    }
    setHeightError("");
    setStep("front");
  }

  async function send(retry = true): Promise<void> {
    if (!front) return;
    setGeneralError(null);
    setPhotoError({});
    setStep("analysing");
    const body = new FormData();
    body.set("front", front);
    if (side) body.set("side", side);
    body.set("height_cm", height);
    body.set("fit_preference", preference);
    let response: Response;
    try {
      response = await fetch("/api/fit/estimate", { method: "POST", body });
    } catch {
      setGeneralError(GENERAL_ERRORS.unavailable);
      setStep("side");
      return;
    }
    const data: unknown = await response.json().catch(() => null);
    if (response.ok) {
      setEstimate(data as FitEstimate);
      setStep("review");
      return;
    }
    const detail = (data as { detail?: FitApiError } | null)?.detail;
    const code = detail?.code ?? "unavailable";
    if (response.status === 401) {
      // The access token expired: renew the session once, then retry.
      if (retry && (await ensureFitSession())) return send(false);
      router.push("/login?next=/fit&reason=expired");
      return;
    }
    if (detail?.photo === "front" || detail?.photo === "side") {
      setPhotoError({ [detail.photo]: detail.message });
      setStep(detail.photo);
      return;
    }
    if (code === "invalid_fit_height") {
      setHeightError(detail?.message ?? "Please check your height.");
      setStep("details");
      return;
    }
    setGeneralError(GENERAL_ERRORS[code] ?? detail?.message ?? GENERAL_ERRORS.unavailable);
    setStep("side");
  }

  const current = step === "analysing" ? "side" : step;

  return (
    <div className="mx-auto max-w-3xl">
      <ol className="flex flex-wrap gap-x-2 gap-y-1 text-xs font-semibold" aria-label="Steps">
        {STEPS.map((item, index) => {
          const active = item.key === current;
          const done = STEPS.findIndex((s) => s.key === current) > index;
          return (
            <li
              key={item.key}
              aria-current={active ? "step" : undefined}
              className={`flex items-center gap-1.5 rounded-full px-3 py-1 ${
                active ? "bg-fit text-white" : done ? "bg-fit-soft text-fit-dark" : "bg-sand text-muted"
              }`}
            >
              <span aria-hidden="true">{index + 1}</span>
              {item.label}
              {done && <span className="sr-only">(done)</span>}
            </li>
          );
        })}
      </ol>

      <div className="mt-5 rounded-2xl border border-line bg-white p-5 sm:p-7">
        {step === "details" && (
          <form onSubmit={submitDetails} noValidate>
            <StepHeading ref={heading}>Your height</StepHeading>
            <p className="mt-1 text-sm text-muted">
              Your height sets the scale of the photos, so please enter it as accurately as you can
              (without shoes).
            </p>
            <div className="mt-5 grid gap-5 sm:grid-cols-2">
              <TextField
                label="Height (cm)"
                name="height_cm"
                type="number"
                inputMode="numeric"
                min={HEIGHT_MIN}
                max={HEIGHT_MAX}
                step={1}
                required
                value={height}
                onChange={(event) => setHeight(event.target.value)}
                error={heightError}
                hint={`Between ${HEIGHT_MIN} and ${HEIGHT_MAX} cm.`}
              />
              <SelectField
                label="Shoe size (EU, optional)"
                name="shoe_size_eu"
                value={shoe}
                onChange={(event) => setShoe(event.target.value)}
                hint="Entered by you. Photos are never used for shoe sizes."
              >
                <option value="">Add later</option>
                {SHOE_SIZES.map((size) => (
                  <option key={size} value={size}>
                    EU {size}
                  </option>
                ))}
              </SelectField>
            </div>
            <div className="mt-5">
              <PreferenceField value={preference} onChange={setPreference} />
            </div>
            <div className="mt-6 flex justify-end">
              <PrimaryButton type="submit">Continue to front photo</PrimaryButton>
            </div>
          </form>
        )}

        {step === "front" && (
          <div>
            <StepHeading ref={heading}>Front photo</StepHeading>
            <Tips items={FRONT_TIPS} label="How to take the front photo" />
            <div className="mt-5">
              <PhotoPicker
                view="front"
                file={front}
                onChange={(file) => {
                  setFront(file);
                  setPhotoError((e) => ({ ...e, front: undefined }));
                }}
                error={photoError.front}
              />
            </div>
            <StepNav onBack={() => setStep("details")}>
              <PrimaryButton type="button" disabled={!front} onClick={() => setStep("side")}>
                Continue to side photo
              </PrimaryButton>
            </StepNav>
          </div>
        )}

        {(step === "side" || step === "analysing") && (
          <div>
            <StepHeading ref={heading}>Side photo (recommended)</StepHeading>
            <Tips items={SIDE_TIPS} label="How to take the side photo" />
            <p className="mt-3 rounded-lg bg-cream px-3 py-2 text-sm text-ink">
              The side photo is optional, but it measures your body depth. Without it, KamerWear
              assumes typical proportions and the estimate always has <strong>low confidence</strong>.
            </p>
            <div className="mt-5">
              <PhotoPicker
                view="side"
                file={side}
                onChange={(file) => {
                  setSide(file);
                  setPhotoError((e) => ({ ...e, side: undefined }));
                }}
                error={photoError.side}
              />
            </div>
            {generalError && (
              <div role="alert" className="mt-4 rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark">
                <p>{generalError}</p>
                <Link href="/account/fit-profile" className="mt-1 inline-block underline underline-offset-2">
                  Enter my sizes myself
                </Link>
              </div>
            )}
            <div aria-live="polite" className="sr-only">
              {step === "analysing" ? "Analysing your photos. This takes a few seconds." : ""}
            </div>
            <StepNav onBack={() => setStep("front")} backDisabled={step === "analysing"}>
              <PrimaryButton
                type="button"
                onClick={() => send()}
                disabled={!front || step === "analysing"}
                busy={step === "analysing"}
              >
                {step === "analysing"
                  ? "Analysing photos…"
                  : side
                    ? "Get my estimate"
                    : "Continue without side photo"}
              </PrimaryButton>
            </StepNav>
          </div>
        )}

        {step === "review" && estimate && (
          <div>
            <StepHeading ref={heading}>Review your estimate</StepHeading>
            <FitReview
              estimate={estimate}
              initialPreference={preference}
              shoe={shoe}
              savedProfile={profile}
              onRetake={() => {
                setEstimate(null);
                setStep("front");
              }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function StepHeading({ children, ref }: { children: ReactNode; ref: React.Ref<HTMLHeadingElement> }) {
  return (
    <h2 ref={ref} tabIndex={-1} className="flex items-center gap-2 text-xl font-extrabold text-ink outline-none">
      <ScanLine className="size-5 text-fit" aria-hidden="true" />
      {children}
    </h2>
  );
}

function Tips({ items, label }: { items: string[]; label: string }) {
  return (
    <div className="mt-3">
      <h3 className="text-sm font-semibold text-ink">{label}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-muted">
        {items.map((tip) => (
          <li key={tip}>{tip}</li>
        ))}
      </ul>
    </div>
  );
}

function StepNav({
  children,
  onBack,
  backDisabled,
}: {
  children: ReactNode;
  onBack: () => void;
  backDisabled?: boolean;
}) {
  return (
    <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between">
      <button
        type="button"
        onClick={onBack}
        disabled={backDisabled}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold text-muted hover:text-ink disabled:opacity-50"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Back
      </button>
      {children}
    </div>
  );
}

function PrimaryButton({
  children,
  busy,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { busy?: boolean }) {
  return (
    <button
      {...props}
      aria-busy={busy || undefined}
      className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-fit px-5 text-sm font-semibold text-white hover:bg-fit-dark disabled:cursor-not-allowed disabled:opacity-60"
    >
      {busy && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}
