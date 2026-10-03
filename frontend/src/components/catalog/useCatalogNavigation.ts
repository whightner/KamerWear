"use client";

import { useOptimistic, useTransition } from "react";
import { useRouter } from "next/navigation";
import { catalogHref, type CatalogFilters } from "@/lib/catalog";

/**
 * Updates /shop's URL search params, which re-renders the server-filtered
 * results. The returned `filters` update optimistically, so a clicked control
 * shows its new state immediately while the results load.
 */
export function useCatalogNavigation(serverFilters: CatalogFilters) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [filters, setFilters] = useOptimistic(serverFilters);

  function update(patch: Partial<CatalogFilters>) {
    const next = { ...filters, ...patch };
    startTransition(() => {
      setFilters(next);
      router.push(catalogHref(next), { scroll: false });
    });
  }

  return { filters, update, pending };
}
