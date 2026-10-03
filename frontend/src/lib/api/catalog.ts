import { cache } from "react";
import { apiUrl } from "@/lib/api-config";
import type {
  Category,
  PaginatedProducts,
  ProductDetail,
  ProductListItem,
  ProductQuery,
} from "./types";

// Typed access to the catalog API. Server-only: pages call these during
// rendering, so the browser never talks to the API directly.

export type CatalogErrorKind = "not_found" | "invalid_request" | "unavailable";

export class CatalogApiError extends Error {
  constructor(
    readonly kind: CatalogErrorKind,
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "CatalogApiError";
  }
}

export function isNotFound(error: unknown): boolean {
  return error instanceof CatalogApiError && error.kind === "not_found";
}

async function request<T>(path: string): Promise<T> {
  let response: Response;
  try {
    // Seeded demo data can change at any time, so always fetch fresh data.
    response = await fetch(apiUrl(path), {
      cache: "no-store",
      headers: { Accept: "application/json" },
    });
  } catch (cause) {
    // fetch() rejects with a TypeError when the API can't be reached. Anything
    // else (e.g. Next.js' own rendering signals) must propagate untouched.
    if (!(cause instanceof TypeError)) throw cause;
    throw new CatalogApiError(
      "unavailable",
      `Catalog API unreachable at ${apiUrl(path)}: ${String(cause)}`,
    );
  }

  if (response.ok) return (await response.json()) as T;

  if (response.status === 404) {
    throw new CatalogApiError("not_found", `Not found: ${path}`, 404);
  }
  if (response.status === 422) {
    throw new CatalogApiError(
      "invalid_request",
      `Invalid catalog request: ${path}`,
      422,
    );
  }
  throw new CatalogApiError(
    "unavailable",
    `Catalog API error ${response.status} for ${path}`,
    response.status,
  );
}

function toSearchParams(query: ProductQuery): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

export function getCategories(): Promise<Category[]> {
  return request<Category[]>("/categories");
}

export function getProducts(
  query: ProductQuery = {},
): Promise<PaginatedProducts> {
  return request<PaginatedProducts>(`/products${toSearchParams(query)}`);
}

/** Deduplicated per request, so generateMetadata and the page share one call. */
export const getProduct = cache(
  (slug: string): Promise<ProductDetail> =>
    request<ProductDetail>(`/products/${encodeURIComponent(slug)}`),
);

export function getSimilarProducts(
  slug: string,
  limit = 4,
): Promise<ProductListItem[]> {
  return request<ProductListItem[]>(
    `/products/${encodeURIComponent(slug)}/similar?limit=${limit}`,
  );
}
