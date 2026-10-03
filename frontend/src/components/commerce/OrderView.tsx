import Image from "next/image";
import Link from "next/link";
import { formatXaf } from "@/lib/format";
import {
  PAYMENT_METHOD_LABELS,
  formatDateTime,
  paymentStatusLabel,
} from "@/lib/commerce/labels";
import type { OrderDetail } from "@/lib/commerce/types";
import { AddressDetails } from "./AddressDetails";
import { OrderTimeline } from "./OrderTimeline";
import { OrderTotals } from "./OrderTotals";
import { StatusBadge } from "./StatusBadge";

/** Full order: status, tracking, delivery address, purchase-time lines and totals. */
export function OrderView({ order }: { order: OrderDetail }) {
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_360px] lg:items-start">
      <div className="space-y-6">
        <section aria-labelledby="order-items" className="rounded-xl border border-line bg-white p-5 sm:p-6">
          <h2 id="order-items" className="mb-2 text-lg font-bold text-ink">
            Items ({order.item_count})
          </h2>
          <ul className="divide-y divide-line">
            {order.items.map((item) => (
              <li key={item.sku} className="flex gap-4 py-4">
                <div className="relative aspect-[4/5] w-16 shrink-0 overflow-hidden rounded-md bg-[#f2f2f2]">
                  {item.image_path && (
                    <Image src={item.image_path} alt="" fill sizes="64px" className="object-cover" />
                  )}
                </div>
                <div className="min-w-0 flex-1 text-sm">
                  <Link
                    href={`/product/${item.product_slug}`}
                    className="font-semibold text-ink hover:underline"
                  >
                    {item.product_name}
                  </Link>
                  <p className="text-muted">
                    {item.color_name}
                    {item.size && ` · ${item.size}`}
                    <span className="ml-2 text-xs">SKU {item.sku}</span>
                  </p>
                  <p className="text-muted">
                    {item.quantity} × {formatXaf(item.unit_price)}
                  </p>
                </div>
                <p className="text-sm font-bold text-ink">{formatXaf(item.line_total)}</p>
              </li>
            ))}
          </ul>
          <div className="mt-2 border-t border-line pt-4">
            <OrderTotals
              subtotal={order.subtotal}
              deliveryFee={order.delivery_fee}
              discountTotal={order.discount_total}
              total={order.total}
            />
            <p className="mt-2 text-xs text-muted">Prices as they were when you ordered.</p>
          </div>
        </section>

        <div className="grid gap-6 sm:grid-cols-2">
          <section aria-labelledby="order-delivery" className="rounded-xl border border-line bg-white p-5">
            <h2 id="order-delivery" className="mb-2 font-bold text-ink">
              Delivery address
            </h2>
            <AddressDetails address={order.delivery} />
          </section>
          <section aria-labelledby="order-payment" className="rounded-xl border border-line bg-white p-5">
            <h2 id="order-payment" className="mb-2 font-bold text-ink">
              Payment
            </h2>
            <p className="text-sm font-medium text-ink">{PAYMENT_METHOD_LABELS[order.payment_method]}</p>
            <p className="text-sm text-muted">
              {paymentStatusLabel(order.payment_status, order.payment_method)}
            </p>
            <p className="mt-2 text-xs text-muted">{order.payment_note}</p>
          </section>
        </div>
      </div>

      <section aria-labelledby="order-tracking" className="rounded-xl border border-line bg-white p-5 sm:p-6">
        <div className="mb-4 flex items-center justify-between gap-2">
          <h2 id="order-tracking" className="text-lg font-bold text-ink">
            Tracking
          </h2>
          <StatusBadge status={order.status} />
        </div>
        <OrderTimeline order={order} />
        <p className="mt-5 text-xs text-muted">
          Status updates only — live courier location isn&apos;t available. Ordered{" "}
          {formatDateTime(order.created_at)}.
        </p>
      </section>
    </div>
  );
}
