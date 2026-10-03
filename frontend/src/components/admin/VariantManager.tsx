"use client";

import { useActionState, useEffect, useState } from "react";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import {
  saveVariantAction,
  setVariantActiveAction,
  type AdminFormState,
} from "@/lib/admin/actions";
import type { AdminProduct, AdminVariant } from "@/lib/admin/types";
import { formatXaf } from "@/lib/format";
import { ActiveBadge, StockBadge } from "./badges";
import { CheckboxField } from "./fields";
import { StockForm } from "./StockForm";
import { ToggleActive } from "./ToggleActive";

function VariantForm({
  productId,
  variant,
  onDone,
}: {
  productId: number;
  variant?: AdminVariant;
  onDone?: () => void;
}) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(saveVariantAction, {});
  const v = (field: string, fallback: string) =>
    state.error ? (state.values?.[field] ?? fallback) : fallback;
  useEffect(() => {
    if (state.success) onDone?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.at]);

  return (
    <form action={formAction} noValidate className="space-y-3" key={state.success ? state.at : "form"}>
      <input type="hidden" name="product_id" value={productId} />
      {variant && <input type="hidden" name="id" value={variant.id} />}
      <FormMessage error={state.error} success={variant ? undefined : state.success} />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <TextField label="SKU" name="sku" required maxLength={40} placeholder="KLS-WHITE-M" defaultValue={v("sku", variant?.sku ?? "")} error={state.fields?.sku} />
        <TextField label="Size (optional)" name="size" maxLength={10} placeholder="M or 42" defaultValue={v("size", variant?.size ?? "")} hint="Leave empty for one-size items." error={state.fields?.size} />
        <TextField label="Colour name" name="color_name" required maxLength={50} placeholder="White" defaultValue={v("color_name", variant?.color_name ?? "")} error={state.fields?.color_name} />
        <TextField label="Colour (hex)" name="color_hex" required maxLength={7} placeholder="#f5f5f0" defaultValue={v("color_hex", variant?.color_hex ?? "#1b1a19")} error={state.fields?.color_hex} hint="Swatch colour, e.g. #1b1a19." />
        <TextField label="Price override (optional)" name="price_override" inputMode="numeric" placeholder="Uses the product price" defaultValue={v("price_override", variant?.price_override != null ? String(variant.price_override) : "")} error={state.fields?.price_override} />
        {!variant && (
          <TextField label="Starting stock (on hand)" name="on_hand" inputMode="numeric" defaultValue={v("on_hand", "0")} error={state.fields?.on_hand} />
        )}
      </div>
      <CheckboxField label="Active (can be bought)" name="is_active" defaultChecked={state.error ? state.values?.is_active === "on" : (variant?.is_active ?? true)} />
      <div className="flex flex-wrap gap-2">
        <div className="w-full sm:w-44">
          <SubmitButton pendingLabel="Saving…">{variant ? "Save variant" : "Add variant"}</SubmitButton>
        </div>
        {onDone && variant && (
          <button type="button" onClick={onDone} className="h-11 rounded-lg border border-line px-4 text-sm font-semibold text-ink hover:bg-cream">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

export function VariantManager({ product }: { product: AdminProduct }) {
  const [editing, setEditing] = useState<number | null>(null);
  // Open at first when there are no variants; afterwards it stays as the admin left it.
  const [adding, setAdding] = useState(product.variants.length === 0);
  return (
    <div className="space-y-5">
      {product.variants.length === 0 ? (
        <p className="rounded-lg bg-cream px-4 py-3 text-sm text-ink">
          No variants yet. Add at least one colour/size so the product can be bought.
        </p>
      ) : (
        <div className="relative overflow-x-auto">
          <table className="w-full min-w-[860px] text-left text-sm">
            <caption className="sr-only">Variants and stock of {product.name}</caption>
            <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="py-2 pr-3 font-semibold">SKU</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Colour</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Size</th>
                <th scope="col" className="py-2 pr-3 text-right font-semibold">Price</th>
                <th scope="col" className="py-2 pr-3 font-semibold">On hand</th>
                <th scope="col" className="py-2 pr-3 text-right font-semibold">Reserved</th>
                <th scope="col" className="py-2 pr-3 text-right font-semibold">Available</th>
                <th scope="col" className="py-2 pr-3 font-semibold">Status</th>
                <th scope="col" className="py-2 font-semibold"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line align-top">
              {product.variants.map((variant) =>
                editing === variant.id ? (
                  <tr key={variant.id}>
                    <td colSpan={9} className="bg-cream/40 p-4">
                      <h3 className="mb-3 font-bold text-ink">Edit {variant.sku}</h3>
                      <VariantForm productId={product.id} variant={variant} onDone={() => setEditing(null)} />
                    </td>
                  </tr>
                ) : (
                  <tr key={variant.id} className={variant.is_active ? "" : "text-muted"}>
                    <td className="py-2.5 pr-3 font-mono text-xs font-semibold">{variant.sku}</td>
                    <td className="py-2.5 pr-3">
                      <span className="inline-flex items-center gap-2">
                        <span aria-hidden="true" className="size-3.5 rounded-full border border-line" style={{ backgroundColor: variant.color_hex }} />
                        {variant.color_name}
                      </span>
                    </td>
                    <td className="py-2.5 pr-3">{variant.size ?? "One size"}</td>
                    <td className="py-2.5 pr-3 text-right">
                      {formatXaf(variant.price)}
                      {variant.price_override != null && <span className="block text-xs text-muted">override</span>}
                    </td>
                    <td className="py-2.5 pr-3">
                      <StockForm variantId={variant.id} onHand={variant.on_hand} reserved={variant.reserved} label={`On hand for ${variant.sku}`} />
                    </td>
                    <td className="py-2.5 pr-3 text-right">{variant.reserved}</td>
                    <td className="py-2.5 pr-3 text-right">
                      <StockBadge state={variant.stock_state} available={variant.available_quantity} />
                    </td>
                    <td className="py-2.5 pr-3">
                      <ActiveBadge active={variant.is_active} />
                    </td>
                    <td className="py-2.5">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setEditing(variant.id)}
                          aria-label={`Edit ${variant.sku}`}
                          className="h-8 rounded-md border border-line px-3 text-xs font-semibold text-ink hover:bg-cream"
                        >
                          Edit
                        </button>
                        <ToggleActive
                          active={variant.is_active}
                          name={variant.sku}
                          action={(next) => setVariantActiveAction(variant.id, next)}
                        />
                      </div>
                    </td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
      <details className="rounded-lg border border-line p-4" open={adding} onToggle={(event) => setAdding(event.currentTarget.open)}>
        <summary className="cursor-pointer text-sm font-bold text-ink">Add a variant</summary>
        <div className="mt-4">
          <VariantForm productId={product.id} />
        </div>
      </details>
    </div>
  );
}
