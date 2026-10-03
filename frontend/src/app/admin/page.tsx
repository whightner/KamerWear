import Link from "next/link";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { OrdersTable } from "@/components/admin/OrdersTable";
import { StockBadge } from "@/components/admin/badges";
import { adminApi } from "@/lib/admin/api";
import { adminToken } from "@/lib/admin/page";
import { formatXaf } from "@/lib/format";

function Metric({
  label,
  value,
  hint,
  href,
  tone = "default",
}: {
  label: string;
  value: string | number;
  hint?: string;
  href?: string;
  tone?: "default" | "warn" | "alert";
}) {
  const accent =
    tone === "alert" ? "border-l-deal" : tone === "warn" ? "border-l-gold" : "border-l-ink";
  const body = (
    <>
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-1 text-2xl font-extrabold text-ink">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-muted">{hint}</p>}
    </>
  );
  const className = `block rounded-xl border border-l-4 border-line ${accent} bg-white p-4`;
  return href ? (
    <Link href={href} className={`${className} hover:bg-cream/40`}>
      {body}
    </Link>
  ) : (
    <div className={className}>{body}</div>
  );
}

export default async function AdminDashboard() {
  const token = await adminToken("/admin");
  if (!token) return null;
  const [result, visual] = await Promise.all([
    adminApi.overview(token),
    adminApi.visualSearchStatus(token),
  ]);

  return (
    <>
      <AdminHeading title="Dashboard" description="Today's store at a glance." />
      {!result.ok ? (
        <AdminError what="the dashboard" />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Metric
              label="Orders awaiting action"
              value={result.data.metrics.orders_awaiting_action}
              hint="Pending, confirmed or preparing"
              href="/admin/orders?status=pending"
              tone={result.data.metrics.orders_awaiting_action > 0 ? "warn" : "default"}
            />
            <Metric label="Orders today" value={result.data.metrics.orders_today} hint={`${result.data.metrics.orders_in_delivery} in delivery`} href="/admin/orders" />
            <Metric
              label="Order value"
              value={formatXaf(result.data.metrics.order_value)}
              hint={`All non-cancelled orders · ${formatXaf(result.data.metrics.paid_order_value)} marked paid (demo)`}
            />
            <Metric label="Customers" value={result.data.metrics.customers} />
            <Metric
              label="Active products"
              value={result.data.metrics.active_products}
              hint={`${result.data.metrics.inactive_products} inactive`}
              href="/admin/products"
            />
            <Metric label="Active variants" value={result.data.metrics.active_variants} href="/admin/inventory" />
            <Metric
              label="Low-stock variants"
              value={result.data.metrics.low_stock_variants}
              hint={`1–${result.data.metrics.low_stock_threshold} units available`}
              href="/admin/inventory?filter=low"
              tone={result.data.metrics.low_stock_variants > 0 ? "warn" : "default"}
            />
            <Metric
              label="Out-of-stock variants"
              value={result.data.metrics.out_of_stock_variants}
              href="/admin/inventory?filter=out"
              tone={result.data.metrics.out_of_stock_variants > 0 ? "alert" : "default"}
            />
            <Metric
              label="Visual search"
              value={visual.ok ? (visual.data.ready ? "Ready" : "Not ready") : "Unknown"}
              hint={
                visual.ok
                  ? `${visual.data.indexed_images}/${visual.data.active_images} photos indexed${
                      visual.data.unindexed_images.length + visual.data.stale_images.length > 0
                        ? " · update needed"
                        : ""
                    }`
                  : "Status unavailable"
              }
              href="/admin/visual-search"
              tone={
                !visual.ok || !visual.data.ready
                  ? "alert"
                  : visual.data.unindexed_images.length + visual.data.stale_images.length > 0
                    ? "warn"
                    : "default"
              }
            />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-[1fr_380px]">
            <Panel
              title="Recent orders"
              actions={<Link href="/admin/orders" className="text-sm font-semibold text-ink underline underline-offset-2">All orders</Link>}
            >
              <OrdersTable orders={result.data.recent_orders} caption="Five most recent orders" />
            </Panel>
            <Panel
              title="Needs restocking"
              actions={<Link href="/admin/inventory?filter=low" className="text-sm font-semibold text-ink underline underline-offset-2">Inventory</Link>}
            >
              {result.data.low_stock.length === 0 ? (
                <p className="text-sm text-muted">Every active variant has enough stock.</p>
              ) : (
                <ul className="divide-y divide-line text-sm">
                  {result.data.low_stock.map((row) => (
                    <li key={row.variant_id} className="flex items-center justify-between gap-3 py-2">
                      <span className="min-w-0">
                        <span className="block truncate font-medium text-ink">{row.product.name}</span>
                        <span className="block text-xs text-muted">
                          {row.sku} · {row.color_name}
                          {row.size && ` · ${row.size}`}
                        </span>
                      </span>
                      <StockBadge state={row.stock_state} available={row.available_quantity} />
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </>
      )}
    </>
  );
}
