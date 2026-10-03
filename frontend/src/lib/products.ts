import type {
  Gender,
  Product,
  ProductImage,
  SimilarGroup,
} from "@/types/catalog";

export function primaryImage(product: Product): ProductImage {
  return product.colors[0].images[0];
}

export function productHref(product: Product): string {
  return `/product/${product.slug}`;
}

const GENDER_LABELS: Record<Gender, string> = {
  men: "Men",
  women: "Women",
  unisex: "Unisex",
};

/** Short label for cards, e.g. "Men · Hoodie". */
export function productLabel(product: Product): string {
  return `${GENDER_LABELS[product.gender]} · ${product.type}`;
}

export type StockStatus =
  | { kind: "out"; label: "Out of stock" }
  | { kind: "low"; label: string }
  | { kind: "in"; label: "In stock" };

export function stockStatus(product: Product): StockStatus {
  if (product.stock <= 0) return { kind: "out", label: "Out of stock" };
  if (product.stock <= 5)
    return { kind: "low", label: `Only ${product.stock} left` };
  return { kind: "in", label: "In stock" };
}

// Demo "Find Similar": same product group first, then closely related groups.
// No image AI is involved yet.
const RELATED_GROUPS: Record<SimilarGroup, SimilarGroup[]> = {
  sneakers: [],
  tees: [],
  hoodies: ["outerwear"],
  outerwear: ["hoodies"],
  bottoms: [],
  bags: [],
};

export function similarProducts(
  product: Product,
  all: Product[],
  limit = 4,
): Product[] {
  const others = all.filter((p) => p.slug !== product.slug);
  const sameGroup = others.filter((p) => p.group === product.group);
  const related = others.filter((p) =>
    RELATED_GROUPS[product.group].includes(p.group),
  );
  return [...sameGroup, ...related].slice(0, limit);
}
