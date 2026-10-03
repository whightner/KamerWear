import Form from "next/form";
import Link from "next/link";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { Pagination } from "@/components/admin/Pagination";
import { ReturnStatusBadge } from "@/components/returns/ReturnBadges";
import { adminToken, param } from "@/lib/admin/page";
import { returnsApi } from "@/lib/after-sales/api";
import { RETURN_STATUS_LABELS } from "@/lib/after-sales/labels";
import { formatDate } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

const LIMIT = 25;

export default async function AdminReturnsPage({ searchParams }: PageProps<"/admin/returns">) {
  const token = await adminToken("/admin/returns");
  if (!token) return null;
  const sp = await searchParams;
  const filters = {
    q: param(sp.q),
    status: param(sp.status),
    date_from: param(sp.date_from),
    date_to: param(sp.date_to),
  };
  const offset = Number(param(sp.offset)) || 0;
  const result = await returnsApi.adminList(token, { ...filters, limit: LIMIT, offset });
  const control = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";
  const label = "mb-1 block text-xs font-semibold text-ink";

  return (
    <>
      <AdminHeading title="Returns" description="Return requests from customers, newest first." />
      <Panel>
        <Form action="/admin/returns" role="search" aria-label="Filter returns" className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_160px_150px_150px_auto] lg:items-end">
          <div>
            <label htmlFor="returns-q" className={label}>Search</label>
            <input id="returns-q" name="q" defaultValue={filters.q} placeholder="Return or order number, email, name" className={control} />
          </div>
          <div>
            <label htmlFor="returns-status" className={label}>Status</label>
            <select id="returns-status" name="status" defaultValue={filters.status ?? ""} className={control}>
              <option value="">Any status</option>
              {Object.entries(RETURN_STATUS_LABELS).map(([value, text]) => (
                <option key={value} value={value}>{text}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="returns-from" className={label}>From</label>
            <input id="returns-from" type="date" name="date_from" defaultValue={filters.date_from} className={control} />
          </div>
          <div>
            <label htmlFor="returns-to" className={label}>To</label>
            <input id="returns-to" type="date" name="date_to" defaultValue={filters.date_to} className={control} />
          </div>
          <button type="submit" className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">Apply</button>
        </Form>
        {!result.ok ? (
          <AdminError what="returns" />
        ) : result.data.items.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">No returns match.</p>
        ) : (
          <>
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <caption className="sr-only">Returns, newest first</caption>
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th scope="col" className="py-2 pr-3 font-semibold">Return</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Order</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Customer</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Date</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Reasons</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Value</th>
                    <th scope="col" className="py-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {result.data.items.map((item) => (
                    <tr key={item.return_number}>
                      <td className="py-2.5 pr-3">
                        <Link href={`/admin/returns/${item.return_number}`} className="font-semibold text-ink underline-offset-2 hover:underline">
                          {item.return_number}
                        </Link>
                      </td>
                      <td className="py-2.5 pr-3">
                        <Link href={`/admin/orders/${item.order_number}`} className="text-ink underline-offset-2 hover:underline">
                          {item.order_number}
                        </Link>
                      </td>
                      <td className="py-2.5 pr-3">
                        <span className="block text-ink">{item.customer.name}</span>
                        <span className="block text-xs text-muted">{item.customer.email}</span>
                      </td>
                      <td className="py-2.5 pr-3 text-muted">{formatDate(item.created_at)}</td>
                      <td className="py-2.5 pr-3 text-muted">{item.reason_summary} · {item.item_count}</td>
                      <td className="py-2.5 pr-3 text-right font-semibold">{formatXaf(item.return_value)}</td>
                      <td className="py-2.5"><ReturnStatusBadge status={item.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination basePath="/admin/returns" params={filters} total={result.data.total} limit={LIMIT} offset={offset} />
          </>
        )}
      </Panel>
    </>
  );
}
