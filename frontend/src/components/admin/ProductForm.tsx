"use client";

import { useActionState, useState } from "react";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import { saveProductAction, type AdminFormState } from "@/lib/admin/actions";
import type { AdminCategory, AdminProduct } from "@/lib/admin/types";
import { CheckboxField, SelectField, TextAreaField } from "./fields";

function slugify(text: string): string {
  return text
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 120);
}

/** Create or edit a product's core fields (variants, stock and images are separate). */
export function ProductForm({
  product,
  categories,
}: {
  product?: AdminProduct;
  categories: AdminCategory[];
}) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(saveProductAction, {});
  const v = (field: string, fallback: string) => state.values?.[field] ?? fallback;
  const flag = (field: string, fallback: boolean) =>
    state.values ? state.values[field] === "on" : fallback;
  const [slug, setSlug] = useState(product?.slug ?? "");
  const [slugEdited, setSlugEdited] = useState(Boolean(product));

  return (
    <form action={formAction} noValidate className="space-y-6">
      {product && <input type="hidden" name="id" value={product.id} />}
      <FormMessage error={state.error} success={state.success} />

      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-bold uppercase tracking-wide text-muted">Basic information</legend>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label="Name"
            name="name"
            required
            maxLength={120}
            defaultValue={v("name", product?.name ?? "")}
            onChange={(event) => {
              if (!slugEdited) setSlug(slugify(event.target.value));
            }}
            error={state.fields?.name}
          />
          <TextField
            label="Slug"
            name="slug"
            required
            maxLength={120}
            value={slug}
            onChange={(event) => {
              setSlugEdited(true);
              setSlug(event.target.value);
            }}
            hint="Used in the product URL: /product/your-slug. Lowercase letters, digits and dashes."
            error={state.fields?.slug}
          />
          {/* Keyed by value: React's post-action form reset would otherwise put an
              uncontrolled select back on its first default. */}
          <SelectField
            key={`category-${v("category_id", String(product?.category.id ?? categories[0]?.id ?? ""))}`}
            label="Category"
            name="category_id"
            defaultValue={v("category_id", String(product?.category.id ?? categories[0]?.id ?? ""))}
            error={state.fields?.category_id}
          >
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name}
                {category.is_active ? "" : " (inactive)"}
              </option>
            ))}
          </SelectField>
          <SelectField key={`gender-${v("gender", product?.gender ?? "unisex")}`} label="Gender" name="gender" defaultValue={v("gender", product?.gender ?? "unisex")} error={state.fields?.gender}>
            <option value="men">Men</option>
            <option value="women">Women</option>
            <option value="unisex">Unisex</option>
          </SelectField>
          <TextField
            label="Product type"
            name="product_type"
            required
            maxLength={50}
            placeholder="Sneakers, Hoodie, Tote…"
            defaultValue={v("product_type", product?.product_type ?? "")}
            error={state.fields?.product_type}
          />
        </div>
        <TextAreaField
          label="Description"
          name="description"
          maxLength={5000}
          rows={4}
          defaultValue={v("description", product?.description ?? "")}
          error={state.fields?.description}
        />
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-bold uppercase tracking-wide text-muted">Pricing (FCFA)</legend>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label="Price"
            name="base_price"
            inputMode="numeric"
            required
            placeholder="28500"
            defaultValue={v("base_price", product ? String(product.base_price) : "")}
            hint="Whole francs, e.g. 28500 = 28,500 FCFA."
            error={state.fields?.base_price}
          />
          <TextField
            label="Compare-at price (optional)"
            name="compare_at_price"
            inputMode="numeric"
            placeholder="39900"
            defaultValue={v("compare_at_price", product?.compare_at_price ? String(product.compare_at_price) : "")}
            hint="The original price shown crossed out. Must be higher than the price."
            error={state.fields?.compare_at_price}
          />
        </div>
      </fieldset>

      <fieldset className="space-y-4">
        <legend className="mb-1 text-sm font-bold uppercase tracking-wide text-muted">Merchandising</legend>
        <div className="grid gap-4 sm:grid-cols-2">
          {!product && (
            <CheckboxField label="Active (visible in the shop)" name="is_active" defaultChecked={flag("is_active", false)} hint="Leave off until variants, stock and images are ready." />
          )}
          <CheckboxField label="New arrival" name="is_new" defaultChecked={flag("is_new", product?.is_new ?? false)} />
          <CheckboxField label="Featured" name="featured" defaultChecked={flag("featured", product?.featured ?? false)} hint="Shown first in Recommended." />
          <CheckboxField label="Smart Fit available" name="smart_fit" defaultChecked={flag("smart_fit", product?.smart_fit ?? false)} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <TextField
            label="Smart Fit demo size (optional)"
            name="smart_fit_demo_size"
            maxLength={10}
            placeholder="M or 42"
            defaultValue={v("smart_fit_demo_size", product?.smart_fit_demo_size ?? "")}
            error={state.fields?.smart_fit_demo_size}
          />
          <TextField
            label="Search keywords"
            name="search_keywords"
            maxLength={255}
            placeholder="streetwear running"
            defaultValue={v("search_keywords", product?.search_keywords ?? "")}
            hint="Extra words shoppers might search for, separated by spaces."
            error={state.fields?.search_keywords}
          />
        </div>
      </fieldset>

      <div className="sm:w-56">
        <SubmitButton pendingLabel="Saving…">{product ? "Save product" : "Create product"}</SubmitButton>
      </div>
    </form>
  );
}
