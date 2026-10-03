"use client";

import { useActionState, useState } from "react";
import { Pencil, Trash2 } from "lucide-react";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import { deleteFitProfile, saveFitProfile, type FitFormState } from "@/lib/fit/actions";
import type { FitPreference, FitProfile } from "@/lib/fit/types";
import { PreferenceField, SizeSelects } from "./SizeFields";

/** Manual edit (or manual creation) of the Fit Profile. */
export function FitProfileForm({ profile, onCancel }: { profile: FitProfile | null; onCancel?: () => void }) {
  const [state, action] = useActionState<FitFormState, FormData>(saveFitProfile, {});
  const [height, setHeight] = useState(profile ? String(profile.height_cm) : "");
  const [preference, setPreference] = useState<FitPreference>(profile?.fit_preference ?? "regular");
  const [top, setTop] = useState(profile?.top_size ?? "");
  const [bottom, setBottom] = useState(profile?.bottom_size ?? "");
  const [shoe, setShoe] = useState(profile?.shoe_size_eu ? String(profile.shoe_size_eu) : "");
  const heightChanged = profile !== null && height !== String(profile.height_cm);

  return (
    <form action={action} className="space-y-5" aria-label="Edit Fit Profile">
      <TextField
        label="Height (cm)"
        name="height_cm"
        type="number"
        inputMode="numeric"
        min={100}
        max={230}
        required
        value={height}
        onChange={(event) => setHeight(event.target.value)}
        error={state.fields?.height_cm}
        hint={
          heightChanged && profile?.source !== "manual"
            ? "Changing your height removes the dimensions estimated from your photos (they were scaled to your old height)."
            : "Between 100 and 230 cm."
        }
        className="sm:max-w-xs"
      />
      <PreferenceField value={preference} onChange={setPreference} />
      <SizeSelects
        top={top}
        bottom={bottom}
        shoe={shoe}
        onTop={setTop}
        onBottom={setBottom}
        onShoe={setShoe}
        errors={state.fields}
      />
      <FormMessage error={state.error} />
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="sm:w-56">
          <SubmitButton pendingLabel="Saving…">Save sizes</SubmitButton>
        </div>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex h-11 items-center justify-center rounded-lg px-4 text-sm font-semibold text-muted hover:text-ink"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

export function EditFitProfile({ profile }: { profile: FitProfile }) {
  const [open, setOpen] = useState(false);
  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-expanded={false}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-ink"
      >
        <Pencil className="size-4" aria-hidden="true" />
        Edit sizes
      </button>
    );
  }
  return (
    <div className="w-full rounded-xl border border-line bg-white p-5">
      <FitProfileForm profile={profile} onCancel={() => setOpen(false)} />
    </div>
  );
}

export function DeleteFitProfile() {
  const [confirming, setConfirming] = useState(false);
  const [state, action] = useActionState<FitFormState, FormData>(deleteFitProfile, {});
  if (!confirming) {
    return (
      <button
        type="button"
        onClick={() => setConfirming(true)}
        className="inline-flex h-11 items-center justify-center gap-2 rounded-lg px-4 text-sm font-semibold text-deal-dark hover:bg-deal-soft"
      >
        <Trash2 className="size-4" aria-hidden="true" />
        Delete Fit Profile
      </button>
    );
  }
  return (
    <form
      action={action}
      aria-labelledby="delete-fit-title"
      className="w-full rounded-xl border border-deal/30 bg-deal-soft p-4"
    >
      <p id="delete-fit-title" className="text-sm font-semibold text-deal-dark">
        Delete your Fit Profile?
      </p>
      <p className="mt-1 text-sm text-ink">
        This removes your saved sizes and any stored estimates. Your KamerWear account, orders
        and addresses stay.
      </p>
      <FormMessage error={state.error} />
      <div className="mt-3 flex flex-wrap gap-3">
        <button
          type="submit"
          className="inline-flex h-10 items-center rounded-lg bg-deal px-4 text-sm font-semibold text-white hover:bg-deal-dark"
        >
          Yes, delete it
        </button>
        <button
          type="button"
          onClick={() => setConfirming(false)}
          autoFocus
          className="inline-flex h-10 items-center rounded-lg px-4 text-sm font-semibold text-ink hover:bg-white"
        >
          Keep my Fit Profile
        </button>
      </div>
    </form>
  );
}
