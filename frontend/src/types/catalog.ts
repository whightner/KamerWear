export type Gender = "men" | "women" | "unisex";
export type ProductCategory = "shoes" | "clothing" | "accessories";
/** Used by the demo "Find Similar" flow to keep matches relevant. */
export type SimilarGroup =
  | "sneakers"
  | "tees"
  | "hoodies"
  | "outerwear"
  | "bottoms"
  | "bags";

export interface ProductImage {
  /** Path under /public. */
  src: string;
  alt: string;
}

export interface ProductColor {
  slug: string;
  name: string;
  /** CSS colour used for the swatch. */
  swatch: string;
  /** Real photos of this colour only; never duplicated to fake a gallery. */
  images: ProductImage[];
}

export interface Product {
  slug: string;
  name: string;
  description: string;
  gender: Gender;
  category: ProductCategory;
  /** Product type shown on cards, e.g. "Hoodie". */
  type: string;
  group: SimilarGroup;
  /** Current price in whole XAF (FCFA). Always an integer. */
  price: number;
  /** Price before discount in whole XAF, when the product is on sale. */
  oldPrice?: number;
  /** Average rating out of 5. */
  rating: number;
  reviewCount: number;
  /** At least one colour; the first is the default. */
  colors: ProductColor[];
  /** Empty for one-size products. Shoes use EU sizes. */
  sizes: string[];
  soldOutSizes?: string[];
  /** Demo units left across all sizes. */
  stock: number;
  /** Product supports Smart Fit size recommendations. */
  smartFit?: boolean;
  /** Size shown by the Smart Fit demo state (no real Fit Profile yet). */
  smartFitDemoSize?: string;
  isNew?: boolean;
  /** Extra search keywords, e.g. "streetwear". */
  tags?: string[];
}

export interface Category {
  slug: string;
  name: string;
  image: string;
  imageAlt: string;
  href: string;
  badge?: string;
}
