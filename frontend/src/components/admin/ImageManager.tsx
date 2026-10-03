"use client";

import { useActionState, useEffect, useState, useTransition } from "react";
import Image from "next/image";
import Link from "next/link";
import { FormMessage, SubmitButton, TextField } from "@/components/auth/fields";
import { deleteImageAction, saveImageAction, type AdminFormState } from "@/lib/admin/actions";
import type { AdminImage, AdminProduct } from "@/lib/admin/types";

function ImageForm({
  product,
  image,
  onDone,
}: {
  product: AdminProduct;
  image?: AdminImage;
  onDone?: () => void;
}) {
  const [state, formAction] = useActionState<AdminFormState, FormData>(saveImageAction, {});
  const v = (field: string, fallback: string) =>
    state.error ? (state.values?.[field] ?? fallback) : fallback;
  const colors = [...new Set(product.variants.map((variant) => variant.color_name))];
  useEffect(() => {
    if (state.success) onDone?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.at]);

  return (
    <form action={formAction} noValidate className="space-y-3" key={state.success ? state.at : "form"}>
      <input type="hidden" name="product_id" value={product.id} />
      {image && <input type="hidden" name="id" value={image.id} />}
      <FormMessage error={state.error} success={image ? undefined : state.success} />
      <div className="grid gap-3 md:grid-cols-2">
        <TextField
          label="Image path"
          name="image_path"
          required
          placeholder={`/images/products/${product.slug}/white-1.webp`}
          defaultValue={v("image_path", image?.image_path ?? "")}
          hint="A file in the web app's public/images/products/ folder (webp, jpg, png or avif)."
          error={state.fields?.image_path}
        />
        <TextField
          label="Alt text"
          name="alt_text"
          required
          maxLength={255}
          placeholder="White linen shirt, front view"
          defaultValue={v("alt_text", image?.alt_text ?? "")}
          error={state.fields?.alt_text}
        />
        <TextField
          label="Position"
          name="position"
          inputMode="numeric"
          placeholder={image ? undefined : "Last"}
          defaultValue={v("position", image ? String(image.position) : "")}
          hint="0 is the first photo. Equal positions keep their upload order."
          error={state.fields?.position}
        />
        <TextField
          label="Colour (optional)"
          name="color_name"
          maxLength={50}
          list={`colors-${product.id}`}
          defaultValue={v("color_name", image?.color_name ?? "")}
          hint="Shown when this colour is selected. Empty = all colours."
          error={state.fields?.color_name}
        />
        <datalist id={`colors-${product.id}`}>
          {colors.map((color) => (
            <option key={color} value={color} />
          ))}
        </datalist>
      </div>
      <div className="flex flex-wrap gap-2">
        <div className="w-full sm:w-44">
          <SubmitButton pendingLabel="Saving…">{image ? "Save image" : "Add image"}</SubmitButton>
        </div>
        {onDone && image && (
          <button type="button" onClick={onDone} className="h-11 rounded-lg border border-line px-4 text-sm font-semibold text-ink hover:bg-cream">
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

function RemoveImage({ image }: { image: AdminImage }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, start] = useTransition();
  const [error, setError] = useState("");
  if (!confirming) {
    return (
      <button type="button" onClick={() => setConfirming(true)} aria-label={`Remove image ${image.alt_text}`} className="h-8 rounded-md px-3 text-xs font-semibold text-deal-dark hover:bg-deal-soft">
        Remove
      </button>
    );
  }
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={pending}
        onClick={() =>
          start(async () => {
            const result = await deleteImageAction(image.id);
            if (!result.ok) setError(result.message);
          })
        }
        className="h-8 rounded-md bg-deal-dark px-3 text-xs font-semibold text-white"
      >
        Confirm remove
      </button>
      <button type="button" onClick={() => setConfirming(false)} className="h-8 rounded-md px-2 text-xs font-semibold text-muted">
        Keep
      </button>
      {error && <span role="alert" className="text-xs text-deal-dark">{error}</span>}
    </span>
  );
}

export function ImageManager({
  product,
  notSearchable,
}: {
  product: AdminProduct;
  /** Image paths missing from the visual search index (null: status unknown). */
  notSearchable: string[] | null;
}) {
  const [editing, setEditing] = useState<number | null>(null);
  // Open at first when there are no images; afterwards it stays as the admin left it.
  const [adding, setAdding] = useState(product.images.length === 0);
  return (
    <div className="space-y-5">
      <p className="text-xs text-muted">
        Images are files of the web app (public/images/products/). Here you manage which files a
        product uses, their order and colour. No upload yet.
      </p>
      {product.images.length === 0 ? (
        <p className="rounded-lg bg-cream px-4 py-3 text-sm text-ink">No images yet.</p>
      ) : (
        <ol className="divide-y divide-line">
          {product.images.map((image) => (
            <li key={image.id} className="py-3">
              {editing === image.id ? (
                <ImageForm product={product} image={image} onDone={() => setEditing(null)} />
              ) : (
                <div className="flex flex-wrap items-center gap-4">
                  <div className="relative h-20 w-16 shrink-0 overflow-hidden rounded-md bg-[#f2f2f2]">
                    <Image src={image.image_path} alt={image.alt_text} fill sizes="64px" unoptimized className="object-cover" />
                  </div>
                  <div className="min-w-0 flex-1 text-sm">
                    <p className="font-medium text-ink">
                      #{image.position} · {image.alt_text}
                    </p>
                    <p className="break-all font-mono text-xs text-muted">{image.image_path}</p>
                    <p className="text-xs text-muted">Colour: {image.color_name ?? "all colours"}</p>
                    {product.is_active && notSearchable?.includes(image.image_path) && (
                      <p className="mt-1 text-xs font-medium text-deal-dark">
                        Not in visual search yet —{" "}
                        <Link href="/admin/visual-search" className="underline underline-offset-2">
                          update the index
                        </Link>
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button type="button" onClick={() => setEditing(image.id)} aria-label={`Edit image ${image.alt_text}`} className="h-8 rounded-md border border-line px-3 text-xs font-semibold text-ink hover:bg-cream">
                      Edit
                    </button>
                    <RemoveImage image={image} />
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
      <details className="rounded-lg border border-line p-4" open={adding} onToggle={(event) => setAdding(event.currentTarget.open)}>
        <summary className="cursor-pointer text-sm font-bold text-ink">Add an image</summary>
        <div className="mt-4">
          <ImageForm product={product} />
        </div>
      </details>
    </div>
  );
}
