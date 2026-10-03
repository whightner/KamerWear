import type { ApiSort, Category, Gender, ProductQuery } from "@/lib/api/types";

// URL state for /shop. The URL is the source of truth for filters, search,
// sorting and page; the catalog API does the actual filtering. These helpers
// only parse the URL, build URLs, and translate them to API parameters.

export const PAGE_SIZE = 12;

export const GENDER_OPTIONS: { value: Gender; label: string }[] = [
  { value: "men", label: "Men" },
  { value: "women", label: "Women" },
  { value: "unisex", label: "Unisex" },
];

export const PRICE_RANGES = [
  { value: "under-10000", label: "Under 10,000 FCFA", min: 0, max: 9999 },
  {
    value: "10000-20000",
    label: "10,000 – 20,000 FCFA",
    min: 10000,
    max: 20000,
  },
  {
    value: "over-20000",
    label: "Over 20,000 FCFA",
    min: 20001,
    max: undefined,
  },
] as const;

export type PriceRange = (typeof PRICE_RANGES)[number]["value"];

/** Size filter options (UI configuration). A size with no products simply returns no results. */
export const SIZE_GROUPS = [
  { label: "Clothing", sizes: ["XS", "S", "M", "L", "XL", "XXL"] },
  { label: "Waist", sizes: ["30", "32", "34", "36"] },
  { label: "Shoes (EU)", sizes: ["39", "40", "41", "42", "43", "44", "45"] },
];

export const SORT_OPTIONS: { value: ApiSort; label: string }[] = [
  { value: "recommended", label: "Recommended" },
  { value: "price-asc", label: "Price: Low to High" },
  { value: "price-desc", label: "Price: High to Low" },
  { value: "rating", label: "Highest Rated" },
  { value: "discount", label: "Biggest Discount" },
];

export interface CatalogFilters {
  q: string;
  /** Backend category slug, e.g. "shoes". */
  category?: string;
  gender?: Gender;
  size?: string;
  price?: PriceRange;
  smartFit: boolean;
  deals: boolean;
  inStock: boolean;
  isNew: boolean;
  sort: ApiSort;
  /** 1-based page number. */
  page: number;
}

type RawParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function oneOf<T extends string>(
  value: string | undefined,
  allowed: readonly { value: T }[],
): T | undefined {
  return allowed.find((option) => option.value === value)?.value;
}

/** Reads URL search params; unknown values are ignored rather than erroring. */
export function parseCatalogParams(params: RawParams): CatalogFilters {
  const category = first(params.category);
  const page = Number.parseInt(first(params.page) ?? "1", 10);
  return {
    q: (first(params.q) ?? "").trim().slice(0, 80),
    category:
      category && /^[a-z0-9-]{1,80}$/.test(category) ? category : undefined,
    gender: oneOf(first(params.gender), GENDER_OPTIONS),
    size: first(params.size)?.slice(0, 10) || undefined,
    price: oneOf(first(params.price), PRICE_RANGES),
    smartFit: first(params.smartfit) === "true",
    deals: first(params.deals) === "true",
    inStock: first(params.instock) === "true",
    isNew: first(params.new) === "true",
    sort: oneOf(first(params.sort), SORT_OPTIONS) ?? "recommended",
    page: Number.isFinite(page) && page > 1 ? Math.min(page, 1000) : 1,
  };
}

/** The inverse of parseCatalogParams; default values are left out. */
export function catalogParams(filters: CatalogFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.q) params.set("q", filters.q);
  if (filters.category) params.set("category", filters.category);
  if (filters.gender) params.set("gender", filters.gender);
  if (filters.size) params.set("size", filters.size);
  if (filters.price) params.set("price", filters.price);
  if (filters.smartFit) params.set("smartfit", "true");
  if (filters.deals) params.set("deals", "true");
  if (filters.inStock) params.set("instock", "true");
  if (filters.isNew) params.set("new", "true");
  if (filters.sort !== "recommended") params.set("sort", filters.sort);
  if (filters.page > 1) params.set("page", String(filters.page));
  return params;
}

export function catalogHref(filters: CatalogFilters): string {
  const query = catalogParams(filters).toString();
  return query ? `/shop?${query}` : "/shop";
}

/** Translates the shop URL state into GET /products query parameters. */
export function toProductQuery(filters: CatalogFilters): ProductQuery {
  const range = PRICE_RANGES.find((r) => r.value === filters.price);
  return {
    q: filters.q || undefined,
    category: filters.category,
    gender: filters.gender,
    size: filters.size,
    min_price: range?.min,
    max_price: range?.max,
    smart_fit: filters.smartFit || undefined,
    on_sale: filters.deals || undefined,
    in_stock: filters.inStock || undefined,
    is_new: filters.isNew || undefined,
    sort: filters.sort,
    limit: PAGE_SIZE,
    offset: (filters.page - 1) * PAGE_SIZE,
  };
}

export function catalogTitle(
  filters: CatalogFilters,
  categories: Category[],
): string {
  if (filters.q) return `Results for “${filters.q}”`;
  if (filters.deals) return "Deals";
  if (filters.isNew) return "New In";
  const category = categories.find((c) => c.slug === filters.category);
  if (category && category.slug !== "clothing") return category.name;
  if (filters.gender === "men") return "Men's Fashion";
  if (filters.gender === "women") return "Women's Fashion";
  if (category) return category.name;
  return "Shop";
}

/** Human-readable list of active filters, each with the URL that removes it. */
export function activeFilterChips(
  filters: CatalogFilters,
  categories: Category[],
): { label: string; href: string }[] {
  const chips: { label: string; href: string }[] = [];
  // Changing filters always returns to the first page.
  const without = (patch: Partial<CatalogFilters>) =>
    catalogHref({ ...filters, ...patch, page: 1 });
  if (filters.q)
    chips.push({ label: `“${filters.q}”`, href: without({ q: "" }) });
  if (filters.category)
    chips.push({
      label:
        categories.find((c) => c.slug === filters.category)?.name ??
        filters.category,
      href: without({ category: undefined }),
    });
  if (filters.gender)
    chips.push({
      label: GENDER_OPTIONS.find((o) => o.value === filters.gender)!.label,
      href: without({ gender: undefined }),
    });
  if (filters.size)
    chips.push({
      label: `Size ${filters.size}`,
      href: without({ size: undefined }),
    });
  if (filters.price)
    chips.push({
      label: PRICE_RANGES.find((r) => r.value === filters.price)!.label,
      href: without({ price: undefined }),
    });
  if (filters.smartFit)
    chips.push({ label: "Smart Fit", href: without({ smartFit: false }) });
  if (filters.deals)
    chips.push({ label: "On sale", href: without({ deals: false }) });
  if (filters.inStock)
    chips.push({ label: "In stock", href: without({ inStock: false }) });
  if (filters.isNew)
    chips.push({ label: "New in", href: without({ isNew: false }) });
  return chips;
}
