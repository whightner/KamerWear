import type { PaymentStatus } from "@/lib/commerce/types";
import type { StockState } from "@/lib/admin/types";

const base = "inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold";

export function ActiveBadge({ active, label }: { active: boolean; label?: string }) {
  return (
    <span className={`${base} ${active ? "bg-fit-soft text-fit-dark" : "bg-sand text-ink"}`}>
      {label ?? (active ? "Active" : "Inactive")}
    </span>
  );
}

export function StockBadge({ state, available }: { state: StockState; available: number }) {
  const styles: Record<StockState, string> = {
    out: "bg-deal-soft text-deal-dark",
    low: "bg-gold-soft text-ink",
    in: "bg-fit-soft text-fit-dark",
  };
  const label = state === "out" ? "Out of stock" : state === "low" ? `Low · ${available}` : "In stock";
  return <span className={`${base} ${styles[state]}`}>{label}</span>;
}

const PAYMENT_STYLES: Record<PaymentStatus, string> = {
  pending: "bg-gold-soft text-ink",
  paid: "bg-fit-soft text-fit-dark",
  failed: "bg-deal-soft text-deal-dark",
  refunded: "bg-sand text-ink",
};

export function PaymentBadge({ status }: { status: PaymentStatus }) {
  return (
    <span className={`${base} ${PAYMENT_STYLES[status]}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
