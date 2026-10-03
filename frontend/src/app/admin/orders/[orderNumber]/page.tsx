import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { OrderStatusForm, PaymentStatusForm } from "@/components/admin/OrderActions";
import { PaymentBadge } from "@/components/admin/badges";
import { AddressDetails } from "@/components/commerce/AddressDetails";
import { OrderTimeline } from "@/components/commerce/OrderTimeline";
import { OrderTotals } from "@/components/commerce/OrderTotals";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { adminApi } from "@/lib/admin/api";
import { adminToken } from "@/lib/admin/page";
import { ORDER_STATUS_LABELS, PAYMENT_METHOD_LABELS, formatDateTime } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export default async function AdminOrderPage({ params }: PageProps<"/admin/orders/[orderNumber]">) {
  const { orderNumber } = await params;
  const number = decodeURIComponent(orderNumber);
  const token = await adminToken(`/admin/orders/${orderNumber}`);
  if (!token) return null;
  const result = await adminApi.order(token, number);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <AdminError what="this order" />;
  const order = result.data;

  return (
    <>
      <AdminHeading
        title={`Order ${order.order_number}`}
        description={`Placed ${formatDateTime(order.created_at)} · ${order.item_count} items · ${formatXaf(order.total)}`}
        actions={<Link href="/admin/orders" className="text-sm font-semibold text-ink underline underline-offset-2">All orders</Link>}
      />
      <div className="mb-6 flex flex-wrap items-center gap-2 text-sm">
        <StatusBadge status={order.status} />
        <PaymentBadge status={order.payment_status} />
        <span className="text-muted">{PAYMENT_METHOD_LABELS[order.payment_method]}</span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1fr_380px] xl:items-start">
        <div className="min-w-0 space-y-6">
          <Panel title="Items">
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <caption className="sr-only">Ordered items at purchase-time prices</caption>
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th scope="col" className="py-2 pr-3 font-semibold">Product</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">SKU</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Qty</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Unit price</th>
                    <th scope="col" className="py-2 text-right font-semibold">Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {order.items.map((item) => (
                    <tr key={item.sku}>
                      <td className="py-2.5 pr-3">
                        <span className="flex items-center gap-3">
                          <span className="relative h-12 w-10 shrink-0 overflow-hidden rounded bg-[#f2f2f2]">
                            {item.image_path && <Image src={item.image_path} alt="" fill sizes="40px" unoptimized className="object-cover" />}
                          </span>
                          <span>
                            <span className="block font-medium text-ink">{item.product_name}</span>
                            <span className="block text-xs text-muted">
                              {item.color_name}
                              {item.size && ` · ${item.size}`}
                            </span>
                          </span>
                        </span>
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-xs">{item.sku}</td>
                      <td className="py-2.5 pr-3 text-right">{item.quantity}</td>
                      <td className="py-2.5 pr-3 text-right">{formatXaf(item.unit_price)}</td>
                      <td className="py-2.5 text-right font-semibold">{formatXaf(item.line_total)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3 border-t border-line pt-3 sm:ml-auto sm:max-w-xs">
              <OrderTotals subtotal={order.subtotal} deliveryFee={order.delivery_fee} discountTotal={order.discount_total} total={order.total} />
            </div>
          </Panel>

          <div className="grid gap-6 md:grid-cols-2">
            <Panel title="Customer">
              <p className="text-sm font-medium text-ink">{order.customer.name}</p>
              <p className="text-sm text-muted">{order.customer.email}</p>
              {order.customer.phone && <p className="text-sm text-muted">{order.customer.phone}</p>}
            </Panel>
            <Panel title="Deliver to">
              <AddressDetails address={order.delivery} />
            </Panel>
          </div>

          <Panel title="History">
            <ol className="space-y-3 text-sm">
              {order.status_history.map((event, index) => (
                <li key={`s-${index}`} className="border-l-2 border-line pl-3">
                  <p className="font-semibold text-ink">
                    {ORDER_STATUS_LABELS[event.status]}
                    <span className="ml-2 text-xs font-normal text-muted">
                      {formatDateTime(event.created_at)}
                      {event.changed_by ? ` · ${event.changed_by}` : " · customer checkout"}
                    </span>
                  </p>
                  {event.note && <p className="text-muted">Customer note: {event.note}</p>}
                  {event.internal_note && <p className="text-ink">Internal: {event.internal_note}</p>}
                </li>
              ))}
              {order.payment_history.map((event, index) => (
                <li key={`p-${index}`} className="border-l-2 border-gold pl-3">
                  <p className="font-semibold text-ink">
                    Payment: {event.from_status} → {event.to_status}
                    <span className="ml-2 text-xs font-normal text-muted">
                      {formatDateTime(event.created_at)}
                      {event.changed_by && ` · ${event.changed_by}`} · manual (demo)
                    </span>
                  </p>
                  {event.note && <p className="text-muted">{event.note}</p>}
                </li>
              ))}
            </ol>
          </Panel>
        </div>

        <div className="min-w-0 space-y-6">
          <Panel title="Fulfilment">
            <OrderStatusForm orderNumber={order.order_number} allowed={order.allowed_statuses} />
          </Panel>
          <Panel title="Customer tracking view">
            <OrderTimeline order={{ timeline: order.timeline, is_cancelled: order.status === "cancelled" }} />
          </Panel>
          <Panel title="Payment">
            <PaymentStatusForm orderNumber={order.order_number} allowed={order.allowed_payment_statuses} />
          </Panel>
        </div>
      </div>
    </>
  );
}
