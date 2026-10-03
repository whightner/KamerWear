import Form from "next/form";
import Link from "next/link";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ActiveBadge, StockBadge } from "@/components/admin/badges";
import { Pagination } from "@/components/admin/Pagination";
import { StockForm } from "@/components/admin/StockForm";
import { adminApi } from "@/lib/admin/api";
import { adminToken, param } from "@/lib/admin/page";

const LIMIT = 50;

export default async function AdminInventoryPage({ searchParams }: PageProps<"/admin/inventory">) {
  const token = await adminToken("/admin/inventory");
  if (!token) return null;
  const sp = await searchParams;
  const filters = {
    q: param(sp.q),
    filter: param(sp.filter),
    product_id: param(sp.product_id),
    inactive: param(sp.inactive),
  };
  const offset = Number(param(sp.offset)) || 0;
  const result = await adminApi.inventory(token, {
    q: filters.q,
    product_id: filters.product_id,
    low_stock: filters.filter === "low" || filters.filter === "attention",
    out_of_stock: filters.filter === "out" || filters.filter === "attention",
    include_inactive: filters.inactive === "true",
    limit: LIMIT,
    offset,
  });
  const threshold = result.ok ? result.data.low_stock_threshold : 5;
  const controlClass = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";

  return (
    <>
      <AdminHeading
        title="Inventory"
        description={`Set the physical stock (on hand). Reserved units belong to placed orders and change only through orders. Available = on hand − reserved; low stock = 1–${threshold} available.`}
      />
      <Panel>
        <Form action="/admin/inventory" role="search" aria-label="Filter inventory" className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_220px_auto_auto] lg:items-end">
          <div>
            <label htmlFor="inventory-q" className="mb-1 block text-xs font-semibold text-ink">Search</label>
            <input id="inventory-q" name="q" defaultValue={filters.q} placeholder="Product, SKU or colour" className={controlClass} />
          </div>
          <div>
            <label htmlFor="inventory-filter" className="mb-1 block text-xs font-semibold text-ink">Stock</label>
            <select id="inventory-filter" name="filter" defaultValue={filters.filter ?? ""} className={controlClass}>
              <option value="">All stock levels</option>
              <option value="attention">Low or out of stock</option>
              <option value="low">Low stock only</option>
              <option value="out">Out of stock only</option>
            </select>
          </div>
          <label className="flex h-10 items-center gap-2 text-sm font-semibold text-ink">
            <input type="checkbox" name="inactive" value="true" defaultChecked={filters.inactive === "true"} className="size-4 accent-ink" />
            Include inactive
          </label>
          {filters.product_id && <input type="hidden" name="product_id" value={filters.product_id} />}
          <button type="submit" className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">Apply</button>
        </Form>

        {!result.ok ? (
          <AdminError what="inventory" />
        ) : result.data.items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No variants match these filters.</p>
        ) : (
          <>
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[880px] text-left text-sm">
                <caption className="sr-only">Stock per variant, lowest availability first</caption>
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th scope="col" className="py-2 pr-3 font-semibold">Product</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">SKU</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Size</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Colour</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">On hand</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Reserved</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Available</th>
                    <th scope="col" className="py-2 font-semibold">Stock</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line align-top">
                  {result.data.items.map((row) => (
                    <tr key={row.variant_id}>
                      <td className="py-2.5 pr-3">
                        <Link href={`/admin/products/${row.product.id}`} className="font-semibold text-ink underline-offset-2 hover:underline">
                          {row.product.name}
                        </Link>
                        {(!row.product.is_active || !row.variant_active) && (
                          <span className="mt-1 block">
                            <ActiveBadge active={false} label={row.product.is_active ? "Variant inactive" : "Product inactive"} />
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-3 font-mono text-xs font-semibold">{row.sku}</td>
                      <td className="py-2.5 pr-3">{row.size ?? "One size"}</td>
                      <td className="py-2.5 pr-3">{row.color_name}</td>
                      <td className="py-2.5 pr-3">
                        <StockForm variantId={row.variant_id} onHand={row.on_hand} reserved={row.reserved} label={`On hand for ${row.sku}`} />
                      </td>
                      <td className="py-2.5 pr-3 text-right">{row.reserved}</td>
                      <td className="py-2.5 pr-3 text-right font-semibold">{row.available_quantity}</td>
                      <td className="py-2.5">
                        <StockBadge state={row.stock_state} available={row.available_quantity} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination basePath="/admin/inventory" params={filters} total={result.data.total} limit={LIMIT} offset={offset} />
          </>
        )}
      </Panel>
    </>
  );
}
