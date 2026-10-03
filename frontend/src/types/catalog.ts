export type Department = "Men" | "Women" | "Shoes" | "Accessories";

export interface Product {
  id: string;
  slug: string;
  name: string;
  department: Department;
  /** Product type shown on cards, e.g. "Hoodie". */
  category: string;
  /** Current price in whole XAF (FCFA). Always an integer. */
  price: number;
  /** Price before discount in whole XAF, when the product is on sale. */
  oldPrice?: number;
  /** Average rating out of 5. */
  rating: number;
  reviewCount: number;
  /** Path under /public. */
  image: string;
  imageAlt: string;
  sizes: string[];
  /** Product supports Smart Fit size recommendations. */
  smartFit?: boolean;
  stockHint?: string;
}

export interface Category {
  slug: string;
  name: string;
  image: string;
  imageAlt: string;
  href: string;
  badge?: string;
}
