import Link from "next/link";
import { notFound } from "next/navigation";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ReturnActions } from "@/components/admin/ReturnActions";
import { PaymentBadge } from "@/components/admin/badges";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { ReturnStatusBadge } from "@/components/returns/ReturnBadges";
import { ReturnHistory } from "@/components/returns/ReturnHistory";
import { ReturnItems } from "@/components/returns/ReturnItems";
import { adminToken } from "@/lib/admin/page";
import { returnsApi } from "@/lib/after-sales/api";
import { formatDateTime } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export default async function AdminReturnPage({ params }: PageProps<"/admin/returns/[returnNumber]">) {
  const { returnNumber } = await params;
  const number = decodeURIComponent(returnNumber);
  const token = await adminToken(`/admin/returns/${returnNumber}`);
  if (!token) return null;
  const result = await returnsApi.adminDetail(token, number);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <AdminError what="this return" />;
  const d = result.data;
  const restockById = new Map(d.items.map((item) => [item.id, item.restock]));

  return (
    <>
      <AdminHeading
        title={`Return ${d.return_number}`}
        description={`Requested ${formatDateTime(d.created_at)} · ${d.reason_summary}`}
        actions={<ReturnStatusBadge status={d.status} />}
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
        <div className="min-w-0 space-y-6">
          <Panel title="Items">
            <ReturnItems
              items={d.items}
              extra={(item) => {
                const restock = restockById.get(item.id);
                return restock === null || restock === undefined ? null : (
                  <p className="mt-1 text-xs font-semibold text-ink">
                    {restock ? "Restocked (+on hand)" : "Not restocked"}
                  </p>
                );
              }}
            />
            <dl className="mt-2 grid grid-cols-[1fr_auto] gap-y-1 border-t border-line pt-3 text-sm">
              <dt className="text-muted">Return value (purchase-time prices)</dt>
              <dd className="text-right font-bold text-ink">{formatXaf(d.return_value)}</dd>
              {d.refunded_amount !== null && (
                <>
                  <dt className="text-muted">Demo refund recorded</dt>
                  <dd className="text-right font-bold text-ink">{formatXaf(d.refunded_amount)}</dd>
                </>
              )}
            </dl>
            {d.refund_note && <p className="mt-2 rounded-lg bg-gold-soft px-3 py-2 text-xs text-ink">{d.refund_note}</p>}
            {d.customer_note && (
              <p className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-cream p-3 text-sm text-ink">
                <span className="font-semibold">Customer note: </span>
                {d.customer_note}
              </p>
            )}
          </Panel>
          <Panel title="Status history">
            <ReturnHistory events={d.history} label="Return history with internal notes" />
          </Panel>
        </div>
        <div className="min-w-0 space-y-6">
          <Panel title="Next step">
            <ReturnActions detail={d} />
          </Panel>
          <Panel title="Customer and order">
            <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
              <dt className="text-muted">Customer</dt>
              <dd className="min-w-0 break-words text-ink">{d.customer.name}<br /><span className="text-xs text-muted">{d.customer.email}</span></dd>
              <dt className="text-muted">Order</dt>
              <dd><Link href={`/admin/orders/${d.order.order_number}`} className="font-semibold text-ink underline underline-offset-2">{d.order.order_number}</Link></dd>
              <dt className="text-muted">Order status</dt>
              <dd><StatusBadge status={d.order.status} /></dd>
              <dt className="text-muted">Payment</dt>
              <dd><PaymentBadge status={d.order.payment_status} /></dd>
              <dt className="text-muted">Delivered</dt>
              <dd className="text-ink">{d.order.delivered_at ? formatDateTime(d.order.delivered_at) : "—"}</dd>
              <dt className="text-muted">Order total</dt>
              <dd className="text-ink">{formatXaf(d.order.total)} <span className="text-xs text-muted">(delivery {formatXaf(d.order.delivery_fee)}, not refunded)</span></dd>
            </dl>
            <Link
              href={`/admin/support?q=${encodeURIComponent(d.return_number)}`}
              className="mt-3 inline-block text-sm font-semibold text-ink underline underline-offset-2"
            >
              Support conversations about this return
            </Link>
          </Panel>
        </div>
      </div>
    </>
  );
}
