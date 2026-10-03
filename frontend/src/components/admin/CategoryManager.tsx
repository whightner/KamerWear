"use client";

import { useActionState, useEffect, useState } from "react";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import {
  saveCategoryAction,
  setCategoryActiveAction,
  type AdminFormState,
} from "@/lib/admin/actions";
import type { AdminCategory } from "@/lib/admin/types";
import { ActiveBadge } from "./badges";
import { CheckboxField, TextAreaField } from "./fields";
import { ToggleActive } from "./ToggleActive";

function CategoryForm({ category, onDone }: { category?: AdminCategory; onDone?: () => void }) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(saveCategoryAction, {});
  const v = (field: string, fallback: string) =>
    state.error ? (state.values?.[field] ?? fallback) : fallback;
  useEffect(() => {
    if (state.success) onDone?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.at]);
  return (
    <form action={formAction} noValidate className="space-y-3" key={state.success ? state.at : "form"}>
      {category && <input type="hidden" name="id" value={category.id} />}
      <FormMessage error={state.error} success={category ? undefined : state.success} />
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField label="Name" name="name" required maxLength={80} defaultValue={v("name", category?.name ?? "")} error={state.fields?.name} />
        <TextField label="Slug" name="slug" required maxLength={120} placeholder="bags" defaultValue={v("slug", category?.slug ?? "")} hint="Used in shop links: /shop?category=slug" error={state.fields?.slug} />
      </div>
      <TextAreaField label="Description (optional)" name="description" maxLength={1000} rows={2} defaultValue={v("description", category?.description ?? "")} error={state.fields?.description} />
      <CheckboxField label="Active (shown in the shop)" name="is_active" defaultChecked={state.error ? state.values?.is_active === "on" : (category?.is_active ?? true)} />
      <div className="flex flex-wrap gap-2">
        <div className="w-full sm:w-44">
          <SubmitButton pendingLabel="Saving…">{category ? "Save category" : "Create category"}</SubmitButton>
        </div>
        {onDone && category && (
          <button type="button" onClick={onDone} className="h-11 rounded-lg border border-line px-4 text-sm font-semibold text-ink hover:bg-cream">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

export function CategoryManager({ categories }: { categories: AdminCategory[] }) {
  const [editing, setEditing] = useState<number | null>(null);
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_380px] xl:items-start">
      <section aria-label="Categories" className="min-w-0 rounded-xl border border-line bg-white p-4 sm:p-5">
        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[620px] text-left text-sm">
            <caption className="sr-only">Categories</caption>
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="py-2 pr-3 font-semibold">Category</th>
                <th scope="col" className="py-2 pr-3 text-right font-semibold">Products</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Status</th>
                <th scope="col" className="py-2 font-semibold"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line align-top">
              {categories.map((category) =>
                editing === category.id ? (
                  <tr key={category.id}>
                    <td colSpan={4} className="bg-cream/40 p-4">
                      <h3 className="mb-3 font-bold text-ink">Edit {category.name}</h3>
                      <CategoryForm category={category} onDone={() => setEditing(null)} />
                    </td>
                  </tr>
                ) : (
                  <tr key={category.id}>
                    <td className="py-2.5 pr-3">
                      <span className="block font-semibold text-ink">{category.name}</span>
                      <span className="block text-xs text-muted">/{category.slug}</span>
                      {category.description && <span className="block text-xs text-muted">{category.description}</span>}
                    </td>
                    <td className="py-2.5 pr-3 text-right">
                      {category.active_product_count}
                      <span className="text-xs text-muted"> / {category.product_count}</span>
                      <span className="sr-only"> active of all products</span>
                    </td>
                    <td className="py-2.5 pr-3">
                      <ActiveBadge active={category.is_active} />
                    </td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => setEditing(category.id)} aria-label={`Edit ${category.name}`} className="h-8 rounded-md border border-line px-3 text-xs font-semibold text-ink hover:bg-cream">
                          Edit
                        </button>
                        <ToggleActive active={category.is_active} name={category.name} action={(next) => setCategoryActiveAction(category.id, next)} />
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs text-muted">
          Deactivating a category hides it and its products from the shop. Nothing is deleted.
        </p>
      </section>
      <section aria-labelledby="new-category" className="min-w-0 rounded-xl border border-line bg-white p-4 sm:p-5">
        <h2 id="new-category" className="mb-4 text-base font-bold text-ink">New category</h2>
        <CategoryForm />
      </section>
    </div>
  );
}
