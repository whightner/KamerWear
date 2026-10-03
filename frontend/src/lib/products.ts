import type { Gender, ProductListItem } from "@/lib/api/types";

// Presentation helpers for API products. No catalog data lives here.

export function productHref(product: Pick<ProductListItem, "slug">): string {
  return `/product/${product.slug}`;
}

const GENDER_LABELS: Record<Gender, string> = {
  men: "Men",
  women: "Women",
  unisex: "Unisex",
};

/** Short label for cards, e.g. "Men · Hoodie". */
export function productLabel(product: ProductListItem): string {
  return `${GENDER_LABELS[product.gender]} · ${product.product_type}`;
}

export type StockStatus =
  | { kind: "out"; label: "Out of stock" }
  | { kind: "low"; label: string }
  | { kind: "in"; label: "In stock" };

/** Turns an API availability number into a label (the API computes the number). */
export function stockStatus(availableQuantity: number): StockStatus {
  if (availableQuantity <= 0) return { kind: "out", label: "Out of stock" };
  if (availableQuantity <= 5)
    return { kind: "low", label: `Only ${availableQuantity} left` };
  return { kind: "in", label: "In stock" };
}

export function isShoe(product: Pick<ProductListItem, "category">): boolean {
  return product.category.slug === "shoes";
}
