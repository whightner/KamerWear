"use client";

import { useState, type ReactNode } from "react";
import Link from "next/link";
import { SlidersHorizontal, X } from "lucide-react";
import {
  CATEGORY_OPTIONS,
  GENDER_OPTIONS,
  PRICE_RANGES,
  type CatalogFilters as Filters,
} from "@/lib/catalog";
import { useCatalogNavigation } from "./useCatalogNavigation";

interface CatalogFiltersProps {
  filters: Filters;
  sizes: string[];
  activeCount: number;
}

export function CatalogFilters({
  filters: serverFilters,
  sizes,
  activeCount,
}: CatalogFiltersProps) {
  const [open, setOpen] = useState(false);
  const { filters, update, pending } = useCatalogNavigation(serverFilters);

  return (
    <div>
      {/* Below desktop the panel collapses behind a button. */}
      <button
        type="button"
        aria-expanded={open}
        aria-controls="catalog-filters"
        onClick={() => setOpen((value) => !value)}
        className="flex h-10 items-center gap-2 rounded-lg border border-line bg-white px-4 text-sm font-semibold lg:hidden"
      >
        {open ? (
          <X className="size-4" aria-hidden="true" />
        ) : (
          <SlidersHorizontal className="size-4" aria-hidden="true" />
        )}
        Filters{activeCount ? ` (${activeCount})` : ""}
      </button>

      <div
        id="catalog-filters"
        className={`${open ? "block" : "hidden"} mt-3 rounded-xl border border-line bg-white p-5 lg:mt-0 lg:block ${pending ? "opacity-70" : ""}`}
        aria-busy={pending}
      >
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold">Filters</h2>
          {activeCount > 0 && (
            <Link
              href="/shop"
              scroll={false}
              className="text-xs font-semibold text-deal hover:text-deal-dark"
            >
              Clear all
            </Link>
          )}
        </div>

        <FilterGroup legend="Category">
          <RadioOption
            name="category"
            label="All"
            checked={!filters.category}
            onChange={() => update({ category: undefined })}
          />
          {CATEGORY_OPTIONS.map((option) => (
            <RadioOption
              key={option.value}
              name="category"
              label={option.label}
              checked={filters.category === option.value}
              onChange={() => update({ category: option.value })}
            />
          ))}
        </FilterGroup>

        <FilterGroup legend="Gender">
          <RadioOption
            name="gender"
            label="All"
            checked={!filters.gender}
            onChange={() => update({ gender: undefined })}
          />
          {GENDER_OPTIONS.map((option) => (
            <RadioOption
              key={option.value}
              name="gender"
              label={option.label}
              checked={filters.gender === option.value}
              onChange={() => update({ gender: option.value })}
            />
          ))}
        </FilterGroup>

        <FilterGroup legend="Size">
          <SizeChip
            label="Any"
            checked={!filters.size}
            onChange={() => update({ size: undefined })}
          />
          {sizeGroups(sizes).map((group) => (
            <div key={group.label}>
              <p className="mb-1.5 text-[11px] text-muted">{group.label}</p>
              <div className="flex flex-wrap gap-1.5">
                {group.sizes.map((size) => (
                  <SizeChip
                    key={size}
                    label={size}
                    checked={filters.size === size}
                    onChange={() => update({ size })}
                  />
                ))}
              </div>
            </div>
          ))}
        </FilterGroup>

        <FilterGroup legend="Price">
          <RadioOption
            name="price"
            label="Any price"
            checked={!filters.price}
            onChange={() => update({ price: undefined })}
          />
          {PRICE_RANGES.map((range) => (
            <RadioOption
              key={range.value}
              name="price"
              label={range.label}
              checked={filters.price === range.value}
              onChange={() => update({ price: range.value })}
            />
          ))}
        </FilterGroup>

        <FilterGroup legend="Show only">
          <CheckboxOption
            label="Smart Fit available"
            checked={filters.smartFit}
            onChange={(checked) => update({ smartFit: checked })}
          />
          <CheckboxOption
            label="On sale"
            checked={filters.deals}
            onChange={(checked) => update({ deals: checked })}
          />
          <CheckboxOption
            label="In stock"
            checked={filters.inStock}
            onChange={(checked) => update({ inStock: checked })}
          />
          <CheckboxOption
            label="New in"
            checked={filters.isNew}
            onChange={(checked) => update({ isNew: checked })}
          />
        </FilterGroup>
      </div>
    </div>
  );
}

/** Splits sizes into clothing letters, waist sizes and EU shoe sizes. */
function sizeGroups(sizes: string[]) {
  const isNumber = (size: string) => /^\d+$/.test(size);
  return [
    { label: "Clothing", sizes: sizes.filter((s) => !isNumber(s)) },
    {
      label: "Waist",
      sizes: sizes.filter((s) => isNumber(s) && Number(s) < 38),
    },
    {
      label: "Shoes (EU)",
      sizes: sizes.filter((s) => isNumber(s) && Number(s) >= 38),
    },
  ].filter((group) => group.sizes.length > 0);
}

function SizeChip({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="inline-block cursor-pointer">
      <input
        type="radio"
        name="size"
        className="peer sr-only"
        checked={checked}
        onChange={onChange}
      />
      <span className="flex h-8 min-w-10 items-center justify-center rounded-md border border-line px-2 text-xs font-semibold text-ink peer-checked:border-ink peer-checked:bg-ink peer-checked:text-white peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ink hover:border-ink/50">
        {label}
      </span>
    </label>
  );
}

function FilterGroup({
  legend,
  children,
}: {
  legend: string;
  children: ReactNode;
}) {
  return (
    <fieldset className="mt-5 border-t border-line pt-4">
      <legend className="float-left mb-2.5 w-full text-xs font-bold uppercase tracking-wider text-muted">
        {legend}
      </legend>
      <div className="clear-left space-y-2">{children}</div>
    </fieldset>
  );
}

function RadioOption({
  name,
  label,
  checked,
  onChange,
}: {
  name: string;
  label: string;
  checked: boolean;
  onChange: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink">
      <input
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
        className="size-4 accent-ink"
      />
      {label}
    </label>
  );
}

function CheckboxOption({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 text-sm text-ink">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-4 rounded accent-ink"
      />
      {label}
    </label>
  );
}
