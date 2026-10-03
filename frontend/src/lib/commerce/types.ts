// Response types of the cart, address, checkout and order APIs.
// They mirror backend/app/schemas/{cart,address,orders}.py: keep them in sync.
// Money is whole XAF (FCFA).

export interface CartLine {
  cart_item_id: number;
  quantity: number;
  variant: { id: number; sku: string; size: string | null; color_name: string };
  product: {
    id: number;
    slug: string;
    name: string;
    category_slug: string;
    image: { image_path: string; alt_text: string } | null;
  };
  unit_price: number;
  line_total: number;
  available_quantity: number;
  /** Why this line can't be ordered right now, or null. */
  issue: string | null;
}

export interface Cart {
  items: CartLine[];
  subtotal: number;
  item_count: number;
  has_issues: boolean;
}

export interface CartAdjustment {
  variant_id: number;
  product_name: string | null;
  requested: number;
  added: number;
  message: string;
}

export interface Address {
  id: number;
  label: string;
  recipient_name: string;
  phone: string;
  country_code: string;
  region: string;
  city: string;
  quarter: string;
  street_or_landmark: string;
  latitude: string | null;
  longitude: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AddressInput {
  label: string;
  recipient_name: string;
  phone: string;
  region: string;
  city: string;
  quarter: string;
  street_or_landmark: string;
  is_default: boolean;
}

export type PaymentMethod = "mobile_money" | "card" | "cash_on_delivery";
export type PaymentStatus = "pending" | "paid" | "failed" | "refunded";
export type OrderStatus =
  | "pending"
  | "confirmed"
  | "preparing"
  | "shipped"
  | "out_for_delivery"
  | "delivered"
  | "cancelled";

export interface Quote {
  items: CartLine[];
  item_count: number;
  subtotal: number;
  delivery_fee: number | null;
  discount_total: number;
  total: number;
  address: Address | null;
  payment_method: PaymentMethod | null;
  payment_note: string | null;
  issues: string[];
  can_place_order: boolean;
}

export interface OrderSummary {
  order_number: string;
  created_at: string;
  status: OrderStatus;
  payment_status: PaymentStatus;
  payment_method: PaymentMethod;
  total: number;
  item_count: number;
}

export interface OrderList {
  items: OrderSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface OrderItem {
  product_id: number | null;
  variant_id: number | null;
  product_name: string;
  product_slug: string;
  sku: string;
  size: string | null;
  color_name: string;
  image_path: string | null;
  unit_price: number;
  quantity: number;
  line_total: number;
}

export interface TimelineStep {
  status: OrderStatus;
  label: string;
  state: "done" | "current" | "upcoming";
  reached_at: string | null;
}

export interface OrderDetail extends OrderSummary {
  subtotal: number;
  delivery_fee: number;
  discount_total: number;
  payment_note: string;
  delivery: {
    label: string;
    recipient_name: string;
    phone: string;
    country_code: string;
    region: string;
    city: string;
    quarter: string;
    landmark: string;
    latitude: string | null;
    longitude: string | null;
  };
  items: OrderItem[];
  status_history: { status: OrderStatus; note: string | null; created_at: string }[];
  timeline: TimelineStep[];
  is_cancelled: boolean;
}
