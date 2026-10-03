import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading } from "@/components/admin/AdminShell";
import { CategoryManager } from "@/components/admin/CategoryManager";
import { adminApi } from "@/lib/admin/api";
import { adminToken } from "@/lib/admin/page";

export default async function AdminCategoriesPage() {
  const token = await adminToken("/admin/categories");
  if (!token) return null;
  const categories = await adminApi.categories(token);
  return (
    <>
      <AdminHeading title="Categories" description="Product counts show active / all products." />
      {categories.ok ? <CategoryManager categories={categories.data} /> : <AdminError what="categories" />}
    </>
  );
}
