"use client";

import { useId } from "react";
import { SelectField } from "@/components/admin/fields";
import {
  BOTTOM_SIZES,
  PREFERENCES,
  SHOE_SIZES,
  TOP_SIZES,
  type FitPreference,
} from "@/lib/fit/types";

// Inputs shared by the review step and the account page. All controlled, so
// values survive a failed save.

const LETTER: Record<string, string> = {
  "28": "XS",
  "30": "S",
  "32": "M",
  "34": "L",
  "36": "XL",
  "38": "XXL",
  "40": "XXL",
};

export function PreferenceField({
  value,
  onChange,
}: {
  value: FitPreference;
  onChange: (value: FitPreference) => void;
}) {
  const id = useId();
  return (
    <fieldset aria-describedby={`${id}-hint`}>
      <legend className="text-sm font-semibold text-ink">Fit preference</legend>
      <p id={`${id}-hint`} className="mt-0.5 text-xs text-muted">
        Only changes the suggestion when you are between two sizes.
      </p>
      <div className="mt-2 grid grid-cols-3 gap-2">
        {PREFERENCES.map((option) => (
          <label
            key={option.value}
            className={`flex cursor-pointer flex-col rounded-lg border px-3 py-2 text-sm has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ink ${
              value === option.value
                ? "border-ink bg-ink text-white"
                : "border-line bg-white text-ink hover:border-ink"
            }`}
          >
            <input
              type="radio"
              name="fit_preference"
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
              className="sr-only"
            />
            <span className="font-semibold">{option.label}</span>
            <span className={`text-xs ${value === option.value ? "text-white/80" : "text-muted"}`}>
              {option.hint}
            </span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

interface SizeSelectsProps {
  top: string;
  bottom: string;
  shoe: string;
  onTop: (value: string) => void;
  onBottom: (value: string) => void;
  onShoe: (value: string) => void;
  errors?: Record<string, string>;
  /** Hints under each select, e.g. "Suggested: M". */
  hints?: { top?: string; bottom?: string; shoe?: string };
}

export function SizeSelects({
  top,
  bottom,
  shoe,
  onTop,
  onBottom,
  onShoe,
  errors = {},
  hints = {},
}: SizeSelectsProps) {
  return (
    <div className="grid gap-4 sm:grid-cols-3">
      <SelectField
        label="Top size"
        name="top_size"
        value={top}
        onChange={(event) => onTop(event.target.value)}
        error={errors.top_size}
        hint={hints.top}
      >
        <option value="">Not set</option>
        {TOP_SIZES.map((size) => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Trouser size"
        name="bottom_size"
        value={bottom}
        onChange={(event) => onBottom(event.target.value)}
        error={errors.bottom_size}
        hint={hints.bottom}
      >
        <option value="">Not set</option>
        {BOTTOM_SIZES.map((size) => (
          <option key={size} value={size}>
            {size} ({LETTER[size]})
          </option>
        ))}
      </SelectField>
      <SelectField
        label="Shoe size (EU)"
        name="shoe_size_eu"
        value={shoe}
        onChange={(event) => onShoe(event.target.value)}
        error={errors.shoe_size_eu}
        hint={hints.shoe ?? "Entered by you. Photos are never used for shoe sizes."}
      >
        <option value="">Not set</option>
        {SHOE_SIZES.map((size) => (
          <option key={size} value={size}>
            EU {size}
          </option>
        ))}
      </SelectField>
    </div>
  );
}
