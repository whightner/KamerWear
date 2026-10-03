import Link from "next/link";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { PAYMENT_METHOD_LABELS, formatDate } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";
import type { AdminOrderSummary } from "@/lib/admin/types";
import { PaymentBadge } from "./badges";

export function OrdersTable({ orders, caption }: { orders: AdminOrderSummary[]; caption: string }) {
  if (orders.length === 0) {
    return <p className="py-6 text-center text-sm text-muted">No orders match.</p>;
  }
  return (
    <div className="relative overflow-x-auto">
      <table className="w-full min-w-[760px] text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
          <tr>
            <th scope="col" className="py-2 pr-3 font-semibold">Order</th>
            <th scope="col" className="py-2 pr-3 font-semibold">Customer</th>
            <th scope="col" className="py-2 pr-3 font-semibold">Date</th>
            <th scope="col" className="py-2 pr-3 font-semibold">City</th>
            <th scope="col" className="py-2 pr-3 text-right font-semibold">Items</th>
            <th scope="col" className="py-2 pr-3 text-right font-semibold">Total</th>
            <th scope="col" className="py-2 pr-3 font-semibold">Payment</th>
            <th scope="col" className="py-2 font-semibold">Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-line">
          {orders.map((order) => (
            <tr key={order.order_number}>
              <td className="py-2.5 pr-3">
                <Link href={`/admin/orders/${order.order_number}`} className="font-semibold text-ink underline-offset-2 hover:underline">
                  {order.order_number}
                </Link>
              </td>
              <td className="py-2.5 pr-3">
                <span className="block text-ink">{order.customer.name}</span>
                <span className="block text-xs text-muted">{order.customer.email}</span>
              </td>
              <td className="py-2.5 pr-3 text-muted">{formatDate(order.created_at)}</td>
              <td className="py-2.5 pr-3 text-muted">{order.city}</td>
              <td className="py-2.5 pr-3 text-right">{order.item_count}</td>
              <td className="py-2.5 pr-3 text-right font-semibold">{formatXaf(order.total)}</td>
              <td className="py-2.5 pr-3">
                <span className="block text-xs text-muted">{PAYMENT_METHOD_LABELS[order.payment_method]}</span>
                <PaymentBadge status={order.payment_status} />
              </td>
              <td className="py-2.5">
                <StatusBadge status={order.status} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
