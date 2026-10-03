import { RETURN_STATUS_LABELS } from "@/lib/after-sales/labels";
import type { ConversationStatus, ReturnStatus } from "@/lib/after-sales/types";

const base = "inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold";

const RETURN_STYLES: Record<ReturnStatus, string> = {
  requested: "bg-gold-soft text-ink",
  approved: "bg-sand text-ink",
  received: "bg-sand text-ink",
  refunded: "bg-fit-soft text-fit-dark",
  rejected: "bg-deal-soft text-deal-dark",
  cancelled: "bg-deal-soft text-deal-dark",
};

export function ReturnStatusBadge({ status }: { status: ReturnStatus }) {
  return <span className={`${base} ${RETURN_STYLES[status]}`}>{RETURN_STATUS_LABELS[status]}</span>;
}

export function ConversationStatusBadge({ status }: { status: ConversationStatus }) {
  return (
    <span className={`${base} ${status === "open" ? "bg-fit-soft text-fit-dark" : "bg-sand text-ink"}`}>
      {status === "open" ? "Open" : "Closed"}
    </span>
  );
}
