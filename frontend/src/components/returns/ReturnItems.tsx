import Image from "next/image";
import { RETURN_REASON_LABELS } from "@/lib/after-sales/labels";
import type { ReturnItem } from "@/lib/after-sales/types";
import { formatXaf } from "@/lib/format";

/** Returned lines with purchase-time prices. `extra` adds an admin column. */
export function ReturnItems({
  items,
  extra,
}: {
  items: ReturnItem[];
  extra?: (item: ReturnItem) => React.ReactNode;
}) {
  return (
    <ul className="divide-y divide-line">
      {items.map((item) => (
        <li key={item.id} className="flex gap-3 py-3">
          <div className="relative size-16 shrink-0 overflow-hidden rounded-lg bg-cream">
            {item.image_path && (
              <Image src={item.image_path} alt="" fill sizes="64px" className="object-cover" />
            )}
          </div>
          <div className="min-w-0 flex-1 text-sm">
            <p className="font-semibold text-ink">{item.product_name}</p>
            <p className="text-xs text-muted">
              {item.color_name}
              {item.size && ` · Size ${item.size}`} · {item.sku}
            </p>
            <p className="mt-1 text-ink">
              {item.quantity} × {formatXaf(item.unit_price)} ={" "}
              <span className="font-semibold">{formatXaf(item.line_value)}</span>
            </p>
            <p className="text-xs text-ink">
              Reason: <span className="font-semibold">{RETURN_REASON_LABELS[item.reason]}</span>
            </p>
            {item.condition_note && (
              <p className="mt-0.5 whitespace-pre-wrap break-words text-xs text-muted">
                “{item.condition_note}”
              </p>
            )}
            {extra?.(item)}
          </div>
        </li>
      ))}
    </ul>
  );
}
