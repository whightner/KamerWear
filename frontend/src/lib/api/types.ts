// Response types of the KamerWear catalog API (FastAPI, /api/v1).
// They mirror backend/app/schemas/catalog.py: keep both in sync.
// Prices are whole XAF (FCFA) integers.

export type Gender = "men" | "women" | "unisex";

export type ApiSort =
  | "recommended"
  | "price-asc"
  | "price-desc"
  | "rating"
  | "discount";

export interface Category {
  id: number;
  name: string;
  slug: string;
}

export interface ProductImage {
  /** Static frontend asset path, e.g. /images/products/<slug>/black-1.webp. */
  image_path: string;
  alt_text: string;
  position: number;
  /** Colour this photo shows; null means it applies to every colour. */
  color_name: string | null;
}

export interface ColorOption {
  name: string;
  hex: string;
}

export interface ProductVariant {
  id: number;
  sku: string;
  /** Null for one-size products. */
  size: string | null;
  color_name: string;
  color_hex: string;
  /** Effective price (variant override or product price). */
  price: number;
  in_stock: boolean;
  /** Computed by the backend (on_hand - reserved, never below 0). */
  available_quantity: number;
}

export interface ProductListItem {
  id: number;
  slug: string;
  name: string;
  category: Category;
  gender: Gender;
  product_type: string;
  price: number;
  compare_at_price: number | null;
  discount_percent: number | null;
  rating_average: number;
  review_count: number;
  smart_fit: boolean;
  is_new: boolean;
  featured: boolean;
  primary_image: ProductImage | null;
  sizes: string[];
  colors: ColorOption[];
  in_stock: boolean;
  available_quantity: number;
}

export interface ProductDetail extends ProductListItem {
  description: string;
  smart_fit_demo_size: string | null;
  images: ProductImage[];
  variants: ProductVariant[];
}

export interface PaginatedProducts {
  items: ProductListItem[];
  total: number;
  limit: number;
  offset: number;
}

/** Query parameters accepted by GET /products. */
export interface ProductQuery {
  category?: string;
  gender?: Gender;
  size?: string;
  min_price?: number;
  max_price?: number;
  smart_fit?: boolean;
  on_sale?: boolean;
  in_stock?: boolean;
  is_new?: boolean;
  q?: string;
  sort?: ApiSort;
  limit?: number;
  offset?: number;
}
