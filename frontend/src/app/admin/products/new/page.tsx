import Link from "next/link";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { ProductForm } from "@/components/admin/ProductForm";
import { adminApi } from "@/lib/admin/api";
import { adminToken } from "@/lib/admin/page";

export default async function NewProductPage() {
  const token = await adminToken("/admin/products/new");
  if (!token) return null;
  const categories = await adminApi.categories(token);

  return (
    <>
      <AdminHeading
        title="New product"
        description="Step 1 of 2: the product details. After saving you can add variants, stock and images, then activate it."
        actions={<Link href="/admin/products" className="text-sm font-semibold text-ink underline underline-offset-2">All products</Link>}
      />
      <Panel>
        {categories.ok ? <ProductForm categories={categories.data} /> : <AdminError what="categories" />}
      </Panel>
    </>
  );
}
