import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink } from "lucide-react";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ActiveBadge } from "@/components/admin/badges";
import { ImageManager } from "@/components/admin/ImageManager";
import { ProductForm } from "@/components/admin/ProductForm";
import { ToggleActive } from "@/components/admin/ToggleActive";
import { VariantManager } from "@/components/admin/VariantManager";
import { setProductActiveAction } from "@/lib/admin/actions";
import { adminApi } from "@/lib/admin/api";
import { adminToken, param } from "@/lib/admin/page";

export default async function EditProductPage({ params, searchParams }: PageProps<"/admin/products/[id]">) {
  const { id } = await params;
  const token = await adminToken(`/admin/products/${id}`);
  if (!token) return null;
  const productId = Number(id);
  if (!Number.isInteger(productId)) notFound();
  const [product, categories] = await Promise.all([
    adminApi.product(token, productId),
    adminApi.categories(token),
  ]);
  if (!product.ok && product.status === 404) notFound();
  if (!product.ok || !categories.ok) return <AdminError what="this product" />;
  const p = product.data;
  const created = param((await searchParams).created) === "1";
  const activeVariants = p.variants.filter((v) => v.is_active).length;

  return (
    <>
      <AdminHeading
        title={p.name}
        description={`${p.category.name} · ${p.product_type} · /${p.slug}`}
        actions={<Link href="/admin/products" className="text-sm font-semibold text-ink underline underline-offset-2">All products</Link>}
      />

      {created && (
        <p role="status" className="mb-4 rounded-lg border border-fit/30 bg-fit-soft px-4 py-3 text-sm font-medium text-fit-dark">
          Product created. Next: add variants with stock, add images, then activate it.
        </p>
      )}

      <section
        aria-label="Product status"
        className={`mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border p-4 ${
          p.visible_in_shop ? "border-fit/30 bg-fit-soft" : "border-line bg-white"
        }`}
      >
        <div className="flex flex-wrap items-center gap-3">
          <ActiveBadge active={p.is_active} />
          <p className="text-sm text-ink">
            {p.visible_in_shop
              ? "Visible in the shop."
              : p.is_active
                ? `Active, but hidden: the category “${p.category.name}” is inactive.`
                : "Inactive: hidden from the shop and can't be bought. Past orders are unaffected."}
            {p.is_active && activeVariants === 0 && " No active variants, so nothing can be bought yet."}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {p.visible_in_shop && (
            <Link href={`/product/${p.slug}`} className="inline-flex items-center gap-1 text-sm font-semibold text-ink underline underline-offset-2">
              View in shop
              <ExternalLink className="size-3.5" aria-hidden="true" />
            </Link>
          )}
          <ToggleActive
            active={p.is_active}
            name={p.name}
            activateLabel="Activate product"
            deactivateLabel="Deactivate product"
            action={setProductActiveAction.bind(null, p.id)}
          />
        </div>
      </section>

      <div className="space-y-6">
        <Panel title={`Variants and stock (${p.variants.length})`}>
          <VariantManager product={p} />
        </Panel>
        <Panel title={`Images (${p.images.length})`}>
          <ImageManager product={p} />
        </Panel>
        <Panel title="Product details">
          <ProductForm product={p} categories={categories.data} />
          <p className="mt-4 text-xs text-muted">
            Rating {p.rating_average} from {p.review_count} reviews is demo data and isn&apos;t edited here.
          </p>
        </Panel>
      </div>
    </>
  );
}
