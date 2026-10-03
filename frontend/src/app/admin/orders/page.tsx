import Form from "next/form";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { OrdersTable } from "@/components/admin/OrdersTable";
import { Pagination } from "@/components/admin/Pagination";
import { adminApi } from "@/lib/admin/api";
import { adminToken, param } from "@/lib/admin/page";
import { ORDER_STATUS_LABELS } from "@/lib/commerce/labels";

const LIMIT = 25;

export default async function AdminOrdersPage({ searchParams }: PageProps<"/admin/orders">) {
  const token = await adminToken("/admin/orders");
  if (!token) return null;
  const sp = await searchParams;
  const filters = {
    q: param(sp.q),
    status: param(sp.status),
    payment_status: param(sp.payment_status),
    city: param(sp.city),
  };
  const offset = Number(param(sp.offset)) || 0;
  const result = await adminApi.orders(token, { ...filters, limit: LIMIT, offset });
  const controlClass = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";
  const labelClass = "mb-1 block text-xs font-semibold text-ink";

  return (
    <>
      <AdminHeading title="Orders" description="All customer orders, newest first." />
      <Panel>
        <Form action="/admin/orders" role="search" aria-label="Filter orders" className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_170px_150px_150px_auto] lg:items-end">
          <div>
            <label htmlFor="orders-q" className={labelClass}>Search</label>
            <input id="orders-q" name="q" defaultValue={filters.q} placeholder="Order number, email, name or phone" className={controlClass} />
          </div>
          <div>
            <label htmlFor="orders-status" className={labelClass}>Status</label>
            <select id="orders-status" name="status" defaultValue={filters.status ?? ""} className={controlClass}>
              <option value="">Any status</option>
              {Object.entries(ORDER_STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{value === "pending" ? "Pending (placed)" : label}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="orders-payment" className={labelClass}>Payment</label>
            <select id="orders-payment" name="payment_status" defaultValue={filters.payment_status ?? ""} className={controlClass}>
              <option value="">Any payment</option>
              <option value="pending">Pending</option>
              <option value="paid">Paid</option>
              <option value="failed">Failed</option>
              <option value="refunded">Refunded</option>
            </select>
          </div>
          <div>
            <label htmlFor="orders-city" className={labelClass}>City</label>
            <input id="orders-city" name="city" defaultValue={filters.city} placeholder="Douala" className={controlClass} />
          </div>
          <button type="submit" className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">Apply</button>
        </Form>
        {!result.ok ? (
          <AdminError what="orders" />
        ) : (
          <>
            <OrdersTable orders={result.data.items} caption="Orders, newest first" />
            <Pagination basePath="/admin/orders" params={filters} total={result.data.total} limit={LIMIT} offset={offset} />
          </>
        )}
      </Panel>
    </>
  );
}
