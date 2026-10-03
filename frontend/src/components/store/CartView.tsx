"use client";

import Image from "next/image";
import Link from "next/link";
import { Minus, Plus, Trash2 } from "lucide-react";
import { ComingSoonButton } from "@/components/storefront/ComingSoonButton";
import { formatXaf } from "@/lib/format";
import { productHref } from "@/lib/products";
import { maxQuantity, useStore } from "./StoreProvider";

export function CartView() {
  const { cart, setQuantity, removeFromCart } = useStore();
  const subtotal = cart.reduce(
    (sum, line) => sum + line.unitPrice * line.quantity,
    0,
  );

  if (cart.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
        <p className="text-lg font-bold text-ink">Your cart is empty</p>
        <p className="mt-1 text-sm text-muted">
          Items you add stay here while you browse (demo cart, not saved after a
          page reload).
        </p>
        <Link
          href="/shop"
          className="mt-5 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
        >
          Browse the shop
        </Link>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_320px] lg:items-start">
      <ul className="divide-y divide-line rounded-xl border border-line bg-white">
        {cart.map((line) => {
          const href = productHref({ slug: line.productSlug });
          const limit = maxQuantity(line.availableQuantity);
          return (
            <li key={line.variantId} className="flex gap-4 p-4">
              <Link
                href={href}
                className="relative aspect-[4/5] w-20 shrink-0 overflow-hidden rounded-lg bg-[#f2f2f2]"
              >
                {line.image && (
                  <Image
                    src={line.image.src}
                    alt={line.image.alt}
                    fill
                    sizes="80px"
                    className="object-cover"
                  />
                )}
              </Link>
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <Link
                  href={href}
                  className="truncate font-semibold text-ink hover:underline"
                >
                  {line.productName}
                </Link>
                <p className="text-sm text-muted">
                  {line.colorName}
                  {line.size &&
                    ` · ${line.categorySlug === "shoes" ? "EU " : ""}${line.size}`}
                  <span className="ml-2 text-xs">SKU {line.sku}</span>
                </p>
                <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
                  <div
                    role="group"
                    aria-label={`Quantity for ${line.productName}`}
                    className="flex h-9 items-center rounded-lg border border-line"
                  >
                    <button
                      type="button"
                      aria-label="Decrease quantity"
                      disabled={line.quantity <= 1}
                      onClick={() =>
                        setQuantity(line.variantId, line.quantity - 1)
                      }
                      className="flex h-full w-9 items-center justify-center disabled:text-line"
                    >
                      <Minus className="size-4" aria-hidden="true" />
                    </button>
                    <span className="w-7 text-center text-sm font-semibold">
                      {line.quantity}
                    </span>
                    <button
                      type="button"
                      aria-label="Increase quantity"
                      disabled={line.quantity >= limit}
                      onClick={() =>
                        setQuantity(line.variantId, line.quantity + 1)
                      }
                      className="flex h-full w-9 items-center justify-center disabled:text-line"
                    >
                      <Plus className="size-4" aria-hidden="true" />
                    </button>
                  </div>
                  <p className="font-bold text-ink">
                    {formatXaf(line.unitPrice * line.quantity)}
                  </p>
                </div>
                {line.quantity >= limit && line.availableQuantity <= 10 && (
                  <p className="text-xs text-deal">
                    Only {line.availableQuantity} available
                  </p>
                )}
              </div>
              <button
                type="button"
                aria-label={`Remove ${line.productName} from cart`}
                onClick={() => removeFromCart(line.variantId)}
                className="self-start rounded-md p-1.5 text-muted hover:bg-cream hover:text-ink"
              >
                <Trash2 className="size-4" aria-hidden="true" />
              </button>
            </li>
          );
        })}
      </ul>

      <aside
        aria-label="Order summary"
        className="rounded-xl border border-line bg-white p-5"
      >
        <h2 className="text-lg font-bold text-ink">Summary</h2>
        <div className="mt-4 flex justify-between text-sm">
          <span className="text-muted">Subtotal</span>
          <span className="font-bold text-ink">{formatXaf(subtotal)}</span>
        </div>
        <p className="mt-1 text-xs text-muted">
          Delivery fees are calculated at checkout. Stock is checked again at
          checkout.
        </p>
        <div className="mt-5">
          <ComingSoonButton
            className="flex h-12 w-full items-center justify-center rounded-lg bg-ink px-6 text-sm font-semibold text-white"
            message="Checkout comes in the next task. No payment is taken in this demo."
            messageClassName="text-muted"
          >
            Proceed to checkout
          </ComingSoonButton>
        </div>
      </aside>
    </div>
  );
}
