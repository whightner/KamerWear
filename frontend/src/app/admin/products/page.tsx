import Form from "next/form";
import Image from "next/image";
import Link from "next/link";
import { Plus } from "lucide-react";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ActiveBadge } from "@/components/admin/badges";
import { Pagination } from "@/components/admin/Pagination";
import { adminApi } from "@/lib/admin/api";
import { adminToken, param } from "@/lib/admin/page";
import { formatXaf } from "@/lib/format";

const LIMIT = 25;

export default async function AdminProductsPage({ searchParams }: PageProps<"/admin/products">) {
  const token = await adminToken("/admin/products");
  if (!token) return null;
  const sp = await searchParams;
  const filters = {
    q: param(sp.q),
    category_id: param(sp.category_id),
    status: param(sp.status),
    low_stock: param(sp.low_stock),
  };
  const offset = Number(param(sp.offset)) || 0;
  const [products, categories] = await Promise.all([
    adminApi.products(token, {
      ...filters,
      low_stock: filters.low_stock === "true",
      limit: LIMIT,
      offset,
    }),
    adminApi.categories(token),
  ]);

  const labelClass = "mb-1 block text-xs font-semibold text-ink";
  const controlClass = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";

  return (
    <>
      <AdminHeading
        title="Products"
        description="Create, edit and (de)activate products. Inactive products stay here but leave the shop."
        actions={
          <Link href="/admin/products/new" className="inline-flex h-10 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">
            <Plus className="size-4" aria-hidden="true" />
            New product
          </Link>
        }
      />
      <Panel>
        <Form action="/admin/products" role="search" aria-label="Filter products" className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_180px_150px_auto_auto] lg:items-end">
          <div>
            <label htmlFor="product-q" className={labelClass}>Search</label>
            <input id="product-q" name="q" defaultValue={filters.q} placeholder="Name, slug or SKU" className={controlClass} />
          </div>
          <div>
            <label htmlFor="product-category" className={labelClass}>Category</label>
            <select id="product-category" name="category_id" defaultValue={filters.category_id ?? ""} className={controlClass}>
              <option value="">All categories</option>
              {categories.ok && categories.data.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="product-status" className={labelClass}>Status</label>
            <select id="product-status" name="status" defaultValue={filters.status ?? ""} className={controlClass}>
              <option value="">Any status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </div>
          <label className="flex h-10 items-center gap-2 text-sm font-semibold text-ink">
            <input type="checkbox" name="low_stock" value="true" defaultChecked={filters.low_stock === "true"} className="size-4 accent-ink" />
            Low stock
          </label>
          <button type="submit" className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">Apply</button>
        </Form>

        {!products.ok ? (
          <AdminError what="products" />
        ) : products.data.items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">No products match these filters.</p>
        ) : (
          <>
            <div className="relative overflow-x-auto">
              <table className="w-full min-w-[820px] text-left text-sm">
                <caption className="sr-only">Products</caption>
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th scope="col" className="w-14 py-2 pr-3 font-semibold"><span className="sr-only">Image</span></th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Product</th>
                    <th scope="col" className="py-2 pr-3 font-semibold">Category</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Price</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Variants</th>
                    <th scope="col" className="py-2 pr-3 text-right font-semibold">Available</th>
                    <th scope="col" className="py-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {products.data.items.map((product) => (
                    <tr key={product.id}>
                      <td className="py-2 pr-3">
                        <div className="relative size-11 overflow-hidden rounded-md bg-[#f2f2f2]">
                          {product.image_path && <Image src={product.image_path} alt="" fill sizes="44px" unoptimized className="object-cover" />}
                        </div>
                      </td>
                      <td className="py-2 pr-3">
                        <Link href={`/admin/products/${product.id}`} className="font-semibold text-ink underline-offset-2 hover:underline">
                          {product.name}
                        </Link>
                        <span className="block text-xs text-muted">/{product.slug}</span>
                      </td>
                      <td className="py-2 pr-3 text-muted">
                        {product.category.name}
                        {!product.category.is_active && <span className="block text-xs">(category inactive)</span>}
                      </td>
                      <td className="py-2 pr-3 text-right font-semibold">{formatXaf(product.base_price)}</td>
                      <td className="py-2 pr-3 text-right">
                        {product.active_variant_count}
                        {product.variant_count !== product.active_variant_count && (
                          <span className="text-xs text-muted"> / {product.variant_count}</span>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-right">
                        {product.available_quantity}
                        {product.low_stock_variant_count > 0 && (
                          <span className="block text-xs font-medium text-deal-dark">
                            {product.low_stock_variant_count} low
                          </span>
                        )}
                      </td>
                      <td className="py-2">
                        <ActiveBadge active={product.is_active} />
                        {product.is_active && !product.visible_in_shop && (
                          <span className="block text-xs text-muted">Hidden: category inactive</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pagination basePath="/admin/products" params={filters} total={products.data.total} limit={LIMIT} offset={offset} />
          </>
        )}
      </Panel>
    </>
  );
}
