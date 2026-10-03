// Returns and support API shapes (see backend/app/schemas/returns.py and support.py).

import type { OrderStatus, PaymentMethod, PaymentStatus } from "@/lib/commerce/types";

export type ReturnStatus =
  | "requested"
  | "approved"
  | "rejected"
  | "received"
  | "refunded"
  | "cancelled";

export type ReturnReason =
  | "wrong_size"
  | "damaged"
  | "wrong_item"
  | "not_as_expected"
  | "changed_mind"
  | "other";

export interface ReturnableItem {
  order_item_id: number;
  product_name: string;
  product_slug: string;
  sku: string;
  size: string | null;
  color_name: string;
  image_path: string | null;
  unit_price: number;
  purchased_quantity: number;
  already_returned: number;
  returnable_quantity: number;
}

export interface ReturnRef {
  return_number: string;
  status: ReturnStatus;
  created_at: string;
}

export interface ReturnEligibility {
  order_number: string;
  eligible: boolean;
  code: string | null;
  message: string | null;
  delivered_at: string | null;
  return_deadline: string | null;
  window_days: number;
  items: ReturnableItem[];
  returns: ReturnRef[];
}

export interface ReturnItem {
  id: number;
  order_item_id: number;
  product_name: string;
  product_slug: string;
  sku: string;
  size: string | null;
  color_name: string;
  image_path: string | null;
  unit_price: number;
  quantity: number;
  line_value: number;
  reason: ReturnReason;
  condition_note: string | null;
}

export interface ReturnSummary {
  return_number: string;
  order_number: string;
  status: ReturnStatus;
  reason_summary: string;
  item_count: number;
  return_value: number;
  created_at: string;
}

export interface ReturnDetail extends ReturnSummary {
  customer_note: string | null;
  updated_at: string;
  resolved_at: string | null;
  refunded_amount: number | null;
  refund_note: string | null;
  can_cancel: boolean;
  items: ReturnItem[];
  history: { status: ReturnStatus; note: string | null; created_at: string }[];
}

export interface Paged<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface CustomerRef {
  id: number;
  email: string;
  name: string;
  phone: string | null;
}

export interface AdminReturnSummary extends ReturnSummary {
  customer: CustomerRef;
}

export interface AdminReturnDetail extends AdminReturnSummary {
  customer_note: string | null;
  updated_at: string;
  resolved_at: string | null;
  refunded_amount: number | null;
  refund_note: string | null;
  order: {
    order_number: string;
    status: OrderStatus;
    payment_status: PaymentStatus;
    payment_method: PaymentMethod;
    total: number;
    delivery_fee: number;
    delivered_at: string | null;
  };
  items: (ReturnItem & { variant_id: number | null; restock: boolean | null })[];
  history: {
    status: ReturnStatus;
    note: string | null;
    internal_note: string | null;
    changed_by: string | null;
    created_at: string;
  }[];
  allowed_actions: ("approve" | "reject" | "receive" | "refund")[];
  can_mark_order_refunded: boolean;
}

// --- Support ---------------------------------------------------------------------

export type SupportSubject = "sizing" | "delivery" | "order_issue" | "return_question" | "other";
export type ConversationStatus = "open" | "closed";
export type SenderRole = "customer" | "store";

export interface SupportMessage {
  id: number;
  sender_role: SenderRole;
  sender_name: string;
  body: string;
  created_at: string;
  read_at: string | null;
}

export interface ConversationSummary {
  conversation_number: string;
  subject: SupportSubject;
  subject_label: string;
  status: ConversationStatus;
  order_number: string | null;
  return_number: string | null;
  last_message_preview: string | null;
  last_message_role: SenderRole | null;
  last_message_at: string;
  unread_count: number;
  created_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  closed_at: string | null;
  messages: SupportMessage[];
  last_message_id: number;
}

export interface AdminConversationSummary extends ConversationSummary {
  customer: CustomerRef;
}

export interface AdminConversationDetail extends AdminConversationSummary {
  closed_at: string | null;
  messages: SupportMessage[];
  last_message_id: number;
  order: { order_number: string; status: OrderStatus; total: number } | null;
  return_request: { return_number: string; status: ReturnStatus; return_value: number } | null;
}

export interface NewMessages {
  status: ConversationStatus;
  messages: SupportMessage[];
  last_message_id: number;
}

export interface AttentionCounts {
  returns_to_process: number;
  conversations_unread: number;
}
