import type { OrderStatus, PaymentMethod, PaymentStatus } from "./types";

// Display labels for order data. Shared by server and client components.

export const ORDER_STATUS_LABELS: Record<OrderStatus, string> = {
  pending: "Order placed",
  confirmed: "Confirmed",
  preparing: "Preparing",
  shipped: "Shipped",
  out_for_delivery: "Out for delivery",
  delivered: "Delivered",
  cancelled: "Cancelled",
};

export const PAYMENT_METHOD_LABELS: Record<PaymentMethod, string> = {
  mobile_money: "Mobile Money",
  card: "Card",
  cash_on_delivery: "Cash on delivery",
};

/** Payment status in plain words. Demo methods never pretend to be paid. */
export function paymentStatusLabel(status: PaymentStatus, method: PaymentMethod): string {
  if (status === "pending") {
    return method === "cash_on_delivery"
      ? "To pay on delivery"
      : "Payment pending (demo — no payment taken)";
  }
  return { paid: "Paid", failed: "Payment failed", refunded: "Refunded" }[status];
}

export const CAMEROON_REGIONS = [
  "Adamawa",
  "Centre",
  "East",
  "Far North",
  "Littoral",
  "North",
  "North-West",
  "South",
  "South-West",
  "West",
] as const;

/** Suggestions for the city field; any city can be typed. */
export const MAJOR_CITIES = [
  "Douala",
  "Yaoundé",
  "Bafoussam",
  "Bamenda",
  "Garoua",
  "Maroua",
  "Ngaoundéré",
  "Bertoua",
  "Buea",
  "Limbe",
  "Kribi",
  "Ebolowa",
];

const dateFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  timeZone: "Africa/Douala",
});
const dateTimeFormat = new Intl.DateTimeFormat("en-GB", {
  day: "numeric",
  month: "short",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  timeZone: "Africa/Douala",
});

export function formatDate(iso: string): string {
  return dateFormat.format(new Date(iso));
}

export function formatDateTime(iso: string): string {
  return dateTimeFormat.format(new Date(iso));
}
