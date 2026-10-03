"use client";

import { useActionState, useEffect, useId } from "react";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import { saveAddressAction, type AddressFormState } from "@/lib/commerce/actions";
import { CAMEROON_REGIONS, MAJOR_CITIES } from "@/lib/commerce/labels";
import type { Address } from "@/lib/commerce/types";

interface Props {
  /** Edit this address; omit to add a new one. */
  address?: Address;
  /** Pre-fills recipient name and phone for a new address. */
  defaults?: { recipient_name?: string; phone?: string };
  onSaved?: (address: Address) => void;
  onCancel?: () => void;
  submitLabel?: string;
}

// Cameroon-style address: region, city, quarter and a landmark, since many
// places have no street number. No map is needed.
export function AddressForm({ address, defaults, onSaved, onCancel, submitLabel }: Props) {
  const [state, formAction] = useActionState<AddressFormState, FormData>(saveAddressAction, {});
  const regionId = useId();
  const citiesId = useId();

  useEffect(() => {
    if (state.address) onSaved?.(state.address);
    // Only react to a new save result.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.address]);

  const value = (field: keyof Address & string, fallback = "") =>
    state.values?.[field] ?? (address ? String(address[field] ?? "") : fallback);
  const regionError = state.fields?.region;

  return (
    <form action={formAction} noValidate className="space-y-4">
      {address && <input type="hidden" name="id" value={address.id} />}
      <FormMessage error={state.error} success={state.address ? undefined : state.success} />
      <div className="grid gap-4 sm:grid-cols-2">
        <TextField
          label="Address name"
          name="label"
          placeholder="Home, Office…"
          maxLength={40}
          required
          defaultValue={value("label", "Home")}
          error={state.fields?.label}
        />
        <TextField
          label="Recipient name"
          name="recipient_name"
          autoComplete="name"
          maxLength={120}
          required
          defaultValue={value("recipient_name", defaults?.recipient_name)}
          error={state.fields?.recipient_name}
        />
        <TextField
          label="Phone number"
          name="phone"
          type="tel"
          autoComplete="tel"
          placeholder="+237 6XX XX XX XX"
          maxLength={30}
          required
          defaultValue={value("phone", defaults?.phone)}
          hint="The courier calls this number on delivery."
          error={state.fields?.phone}
        />
        <div>
          <label htmlFor={regionId} className="mb-1.5 block text-sm font-semibold text-ink">
            Region
          </label>
          {/* Keyed by value so it keeps the submitted region after a failed save
              (React resets uncontrolled selects to their first default). */}
          <select
            key={value("region", "Littoral")}
            id={regionId}
            name="region"
            required
            defaultValue={value("region", "Littoral")}
            aria-invalid={regionError ? true : undefined}
            aria-describedby={regionError ? `${regionId}-error` : undefined}
            className={`h-11 w-full rounded-lg border bg-white px-3 text-sm text-ink outline-none focus:border-ink focus:ring-2 focus:ring-ink/10 ${regionError ? "border-deal" : "border-line"}`}
          >
            {CAMEROON_REGIONS.map((region) => (
              <option key={region} value={region}>
                {region}
              </option>
            ))}
          </select>
          {regionError && (
            <p id={`${regionId}-error`} className="mt-1.5 text-xs font-medium text-deal-dark">
              {regionError}
            </p>
          )}
        </div>
        <TextField
          label="City"
          name="city"
          autoComplete="address-level2"
          list={citiesId}
          maxLength={80}
          required
          placeholder="Douala"
          defaultValue={value("city")}
          error={state.fields?.city}
        />
        <datalist id={citiesId}>
          {MAJOR_CITIES.map((city) => (
            <option key={city} value={city} />
          ))}
        </datalist>
        <TextField
          label="Quarter / neighbourhood"
          name="quarter"
          autoComplete="address-level3"
          maxLength={80}
          required
          placeholder="Bonamoussadi"
          defaultValue={value("quarter")}
          error={state.fields?.quarter}
        />
      </div>
      <TextField
        label="Street or precise landmark"
        name="street_or_landmark"
        autoComplete="street-address"
        maxLength={255}
        required
        placeholder="Near Tradex, blue gate opposite the pharmacy"
        defaultValue={value("street_or_landmark")}
        hint="Describe how the courier can find you: a landmark, building or gate colour."
        error={state.fields?.street_or_landmark}
      />
      {!address?.is_default && (
        <label className="flex items-center gap-2 text-sm text-ink">
          <input
            type="checkbox"
            name="is_default"
            defaultChecked={state.values ? state.values.is_default === "on" : false}
            className="size-4 accent-ink"
          />
          Use as my default delivery address
        </label>
      )}
      <div className="flex flex-wrap gap-3">
        <div className="w-full sm:w-48">
          <SubmitButton pendingLabel="Saving…">{submitLabel ?? "Save address"}</SubmitButton>
        </div>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="h-11 rounded-lg border border-line px-5 text-sm font-semibold text-ink hover:bg-cream"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}
