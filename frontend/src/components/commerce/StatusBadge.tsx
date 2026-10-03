import { ORDER_STATUS_LABELS } from "@/lib/commerce/labels";
import type { OrderStatus } from "@/lib/commerce/types";

const STYLES: Record<OrderStatus, string> = {
  pending: "bg-gold-soft text-ink",
  confirmed: "bg-sand text-ink",
  preparing: "bg-sand text-ink",
  shipped: "bg-sand text-ink",
  out_for_delivery: "bg-sand text-ink",
  delivered: "bg-fit-soft text-fit-dark",
  cancelled: "bg-deal-soft text-deal-dark",
};

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STYLES[status]}`}>
      {ORDER_STATUS_LABELS[status]}
    </span>
  );
}
