import type { Gender, Product, ProductCategory } from "@/types/catalog";
import { discountPercent } from "./format";

// Catalog filtering, search and sorting for /shop. Pure functions, so they
// work on the server (page) and in client components (filter controls).

export const CATEGORY_OPTIONS: { value: ProductCategory; label: string }[] = [
  { value: "shoes", label: "Shoes" },
  { value: "clothing", label: "Clothing" },
  { value: "accessories", label: "Accessories" },
];

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
  { value: "over-20000", label: "Over 20,000 FCFA", min: 20001, max: Infinity },
] as const;

export type PriceRange = (typeof PRICE_RANGES)[number]["value"];

export const SORT_OPTIONS = [
  { value: "recommended", label: "Recommended" },
  { value: "price-asc", label: "Price: Low to High" },
  { value: "price-desc", label: "Price: High to Low" },
  { value: "rating", label: "Highest Rated" },
  { value: "discount", label: "Biggest Discount" },
] as const;

export type SortOption = (typeof SORT_OPTIONS)[number]["value"];

export interface CatalogFilters {
  q: string;
  category?: ProductCategory;
  gender?: Gender;
  size?: string;
  price?: PriceRange;
  smartFit: boolean;
  deals: boolean;
  inStock: boolean;
  isNew: boolean;
  sort: SortOption;
}

export const EMPTY_FILTERS: CatalogFilters = {
  q: "",
  smartFit: false,
  deals: false,
  inStock: false,
  isNew: false,
  sort: "recommended",
};

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
  return {
    q: (first(params.q) ?? "").trim().slice(0, 80),
    category: oneOf(first(params.category), CATEGORY_OPTIONS),
    gender: oneOf(first(params.gender), GENDER_OPTIONS),
    size: first(params.size)?.slice(0, 5) || undefined,
    price: oneOf(first(params.price), PRICE_RANGES),
    smartFit: first(params.smartfit) === "true",
    deals: first(params.deals) === "true",
    inStock: first(params.instock) === "true",
    isNew: first(params.new) === "true",
    sort: oneOf(first(params.sort), SORT_OPTIONS) ?? "recommended",
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
  return params;
}

export function catalogHref(filters: CatalogFilters): string {
  const query = catalogParams(filters).toString();
  return query ? `/shop?${query}` : "/shop";
}

function searchText(product: Product): string[] {
  return [
    product.name,
    product.type,
    product.category,
    product.gender,
    ...product.colors.map((c) => c.name),
    ...(product.tags ?? []),
  ]
    .join(" ")
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

/**
 * Simple keyword search: every word in the query must prefix-match a word of
 * the product (name, type, gender, colours, tags). "shoes" also matches "shoe".
 * Word matching keeps "men" from matching "women".
 */
export function matchesSearch(product: Product, query: string): boolean {
  const words = query
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
  if (words.length === 0) return true;
  const tokens = searchText(product);
  return words.every((word) => {
    const singular =
      word.length > 3 && word.endsWith("s") ? word.slice(0, -1) : word;
    return tokens.some(
      (token) => token.startsWith(word) || token.startsWith(singular),
    );
  });
}

export function filterProducts(
  products: Product[],
  filters: CatalogFilters,
): Product[] {
  const range = PRICE_RANGES.find((r) => r.value === filters.price);
  return products.filter((p) => {
    if (!matchesSearch(p, filters.q)) return false;
    if (filters.category && p.category !== filters.category) return false;
    // Men's and women's views include unisex items such as sneakers and bags.
    if (filters.gender === "unisex" && p.gender !== "unisex") return false;
    if (
      filters.gender &&
      filters.gender !== "unisex" &&
      p.gender !== filters.gender &&
      p.gender !== "unisex"
    )
      return false;
    if (filters.size && !p.sizes.includes(filters.size)) return false;
    if (range && (p.price < range.min || p.price > range.max)) return false;
    if (filters.smartFit && !p.smartFit) return false;
    if (filters.deals && !discountPercent(p.price, p.oldPrice)) return false;
    if (filters.inStock && p.stock <= 0) return false;
    if (filters.isNew && !p.isNew) return false;
    return true;
  });
}

export function sortProducts(products: Product[], sort: SortOption): Product[] {
  const sorted = [...products];
  switch (sort) {
    case "price-asc":
      return sorted.sort((a, b) => a.price - b.price);
    case "price-desc":
      return sorted.sort((a, b) => b.price - a.price);
    case "rating":
      return sorted.sort(
        (a, b) => b.rating - a.rating || b.reviewCount - a.reviewCount,
      );
    case "discount":
      return sorted.sort(
        (a, b) =>
          (discountPercent(b.price, b.oldPrice) ?? 0) -
          (discountPercent(a.price, a.oldPrice) ?? 0),
      );
    default:
      // "Recommended" is simply the curated catalog order, not an algorithm.
      return sorted;
  }
}

const SIZE_ORDER = ["XS", "S", "M", "L", "XL", "XXL"];

/** All sizes used by the catalog: clothing sizes first, then numeric sizes. */
export function availableSizes(products: Product[]): string[] {
  const sizes = [...new Set(products.flatMap((p) => p.sizes))];
  const letters = SIZE_ORDER.filter((s) => sizes.includes(s));
  const numbers = sizes
    .filter((s) => !SIZE_ORDER.includes(s))
    .sort((a, b) => Number(a) - Number(b));
  return [...letters, ...numbers];
}

export function catalogTitle(filters: CatalogFilters): string {
  if (filters.q) return `Results for “${filters.q}”`;
  if (filters.deals) return "Deals";
  if (filters.isNew) return "New In";
  if (filters.category === "shoes") return "Shoes";
  if (filters.category === "accessories") return "Accessories";
  if (filters.gender === "men") return "Men's Fashion";
  if (filters.gender === "women") return "Women's Fashion";
  if (filters.category === "clothing") return "Clothing";
  return "Shop";
}

/** Human-readable list of active filters, each with the URL that removes it. */
export function activeFilterChips(
  filters: CatalogFilters,
): { label: string; href: string }[] {
  const chips: { label: string; href: string }[] = [];
  const without = (patch: Partial<CatalogFilters>) =>
    catalogHref({ ...filters, ...patch });
  if (filters.q)
    chips.push({ label: `“${filters.q}”`, href: without({ q: "" }) });
  if (filters.category)
    chips.push({
      label: CATEGORY_OPTIONS.find((o) => o.value === filters.category)!.label,
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
