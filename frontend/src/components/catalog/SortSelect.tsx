"use client";

import {
  SORT_OPTIONS,
  type CatalogFilters,
  type SortOption,
} from "@/lib/catalog";
import { useCatalogNavigation } from "./useCatalogNavigation";

export function SortSelect({
  filters: serverFilters,
}: {
  filters: CatalogFilters;
}) {
  const { filters, update } = useCatalogNavigation(serverFilters);

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="catalog-sort" className="text-sm text-muted">
        Sort by
      </label>
      <select
        id="catalog-sort"
        value={filters.sort}
        onChange={(event) => update({ sort: event.target.value as SortOption })}
        className="h-10 rounded-lg border border-line bg-white px-3 text-sm font-semibold text-ink"
      >
        {SORT_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
