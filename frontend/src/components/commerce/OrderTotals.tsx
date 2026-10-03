import { formatXaf } from "@/lib/format";

/** Subtotal, delivery, discount and total rows. */
export function OrderTotals({
  subtotal,
  deliveryFee,
  discountTotal,
  total,
}: {
  subtotal: number;
  deliveryFee: number | null;
  discountTotal: number;
  total: number;
}) {
  return (
    <dl className="space-y-2 text-sm">
      <div className="flex justify-between">
        <dt className="text-muted">Subtotal</dt>
        <dd className="font-medium text-ink">{formatXaf(subtotal)}</dd>
      </div>
      <div className="flex justify-between">
        <dt className="text-muted">Delivery</dt>
        <dd className="font-medium text-ink">
          {deliveryFee === null ? "Choose an address" : formatXaf(deliveryFee)}
        </dd>
      </div>
      {discountTotal > 0 && (
        <div className="flex justify-between">
          <dt className="text-muted">Discount</dt>
          <dd className="font-medium text-fit-dark">−{formatXaf(discountTotal)}</dd>
        </div>
      )}
      <div className="flex justify-between border-t border-line pt-3 text-base">
        <dt className="font-bold text-ink">Total</dt>
        <dd className="font-extrabold text-ink">{formatXaf(total)}</dd>
      </div>
    </dl>
  );
}
