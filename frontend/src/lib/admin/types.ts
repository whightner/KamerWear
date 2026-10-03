// Response types of the admin API (/api/v1/admin). They mirror
// backend/app/schemas/admin_catalog.py and admin_store.py: keep them in sync.

import type { Gender } from "@/lib/api/types";
import type {
  OrderItem,
  OrderStatus,
  PaymentMethod,
  PaymentStatus,
  TimelineStep,
} from "@/lib/commerce/types";

export type StockState = "out" | "low" | "in";

export interface AdminCategory {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  product_count: number;
  active_product_count: number;
}

export interface CategoryRef {
  id: number;
  name: string;
  slug: string;
  is_active: boolean;
}

export interface AdminProductListItem {
  id: number;
  name: string;
  slug: string;
  category: CategoryRef;
  base_price: number;
  compare_at_price: number | null;
  is_active: boolean;
  visible_in_shop: boolean;
  image_path: string | null;
  variant_count: number;
  active_variant_count: number;
  available_quantity: number;
  low_stock_variant_count: number;
  updated_at: string;
}

export interface Paged<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface AdminImage {
  id: number;
  image_path: string;
  alt_text: string;
  position: number;
  color_name: string | null;
}

export interface AdminVariant {
  id: number;
  sku: string;
  size: string | null;
  color_name: string;
  color_hex: string;
  price_override: number | null;
  price: number;
  is_active: boolean;
  on_hand: number;
  reserved: number;
  available_quantity: number;
  stock_state: StockState;
}

export interface AdminProduct {
  id: number;
  name: string;
  slug: string;
  category: CategoryRef;
  description: string;
  gender: Gender;
  product_type: string;
  base_price: number;
  compare_at_price: number | null;
  smart_fit: boolean;
  smart_fit_demo_size: string | null;
  is_new: boolean;
  featured: boolean;
  is_active: boolean;
  visible_in_shop: boolean;
  search_keywords: string;
  rating_average: string;
  review_count: number;
  images: AdminImage[];
  variants: AdminVariant[];
  created_at: string;
  updated_at: string;
}

export interface InventoryRow {
  variant_id: number;
  sku: string;
  size: string | null;
  color_name: string;
  variant_active: boolean;
  product: { id: number; name: string; slug: string; is_active: boolean };
  on_hand: number;
  reserved: number;
  available_quantity: number;
  stock_state: StockState;
  updated_at: string | null;
}

export interface InventoryList extends Paged<InventoryRow> {
  low_stock_threshold: number;
}

export interface CustomerRef {
  id: number;
  email: string;
  name: string;
  phone: string | null;
}

export interface AdminOrderSummary {
  order_number: string;
  created_at: string;
  customer: CustomerRef;
  total: number;
  payment_method: PaymentMethod;
  payment_status: PaymentStatus;
  status: OrderStatus;
  city: string;
  item_count: number;
}

export interface AdminOrder extends AdminOrderSummary {
  subtotal: number;
  delivery_fee: number;
  discount_total: number;
  delivery: {
    label: string;
    recipient_name: string;
    phone: string;
    country_code: string;
    region: string;
    city: string;
    quarter: string;
    landmark: string;
  };
  items: OrderItem[];
  status_history: {
    status: OrderStatus;
    note: string | null;
    internal_note: string | null;
    changed_by: string | null;
    created_at: string;
  }[];
  payment_history: {
    from_status: PaymentStatus;
    to_status: PaymentStatus;
    note: string | null;
    changed_by: string | null;
    created_at: string;
  }[];
  timeline: TimelineStep[];
  allowed_statuses: OrderStatus[];
  allowed_payment_statuses: PaymentStatus[];
}

export interface Overview {
  metrics: {
    active_products: number;
    inactive_products: number;
    active_variants: number;
    low_stock_variants: number;
    out_of_stock_variants: number;
    orders_awaiting_action: number;
    orders_in_delivery: number;
    orders_today: number;
    customers: number;
    order_value: number;
    paid_order_value: number;
    low_stock_threshold: number;
  };
  recent_orders: AdminOrderSummary[];
  low_stock: InventoryRow[];
}
