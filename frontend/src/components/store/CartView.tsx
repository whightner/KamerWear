"use client";

import { useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertTriangle, Minus, Plus, Trash2 } from "lucide-react";
import { formatXaf } from "@/lib/format";
import { productHref } from "@/lib/products";
import { maxQuantity, useStore, type CartResult } from "./StoreProvider";

export function CartView() {
  const router = useRouter();
  const {
    cart,
    signedIn,
    cartUnavailable,
    cartPending,
    setQuantity,
    removeFromCart,
  } = useStore();
  const [error, setError] = useState("");
  const subtotal = cart.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
  const hasIssues = cart.some((line) => line.issue);

  async function handle(result: Promise<CartResult>) {
    setError("");
    const outcome = await result;
    if (outcome.ok) return;
    if (outcome.code === "session_expired") {
      router.push("/login?next=%2Fcart&reason=expired");
    } else {
      setError(outcome.message);
    }
  }

  if (cartUnavailable) {
    return (
      <div role="alert" className="rounded-xl border border-line bg-white px-6 py-16 text-center">
        <p className="text-lg font-bold text-ink">We couldn&apos;t load your cart right now.</p>
        <p className="mt-1 text-sm text-muted">Your items are saved. Please try again in a moment.</p>
        <button
          type="button"
          onClick={() => router.refresh()}
          className="mt-5 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
        >
          Try again
        </button>
      </div>
    );
  }

  if (cart.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
        <p className="text-lg font-bold text-ink">Your cart is empty</p>
        <p className="mt-1 text-sm text-muted">
          {signedIn
            ? "Items you add are saved to your account."
            : "Items you add stay here while you browse. Log in to save them to your account."}
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
      <div>
        {error && (
          <p
            role="alert"
            className="mb-4 rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark"
          >
            {error}
          </p>
        )}
        <ul
          aria-busy={cartPending}
          className="divide-y divide-line rounded-xl border border-line bg-white"
        >
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
                  <Link href={href} className="truncate font-semibold text-ink hover:underline">
                    {line.productName}
                  </Link>
                  <p className="text-sm text-muted">
                    {line.colorName}
                    {line.size && ` · ${line.categorySlug === "shoes" ? "EU " : ""}${line.size}`}
                    <span className="ml-2 text-xs">SKU {line.sku}</span>
                  </p>
                  <p className="text-sm text-muted">{formatXaf(line.unitPrice)} each</p>
                  <div className="mt-auto flex flex-wrap items-center justify-between gap-3">
                    <div
                      role="group"
                      aria-label={`Quantity for ${line.productName}`}
                      className="flex h-9 items-center rounded-lg border border-line"
                    >
                      <button
                        type="button"
                        aria-label="Decrease quantity"
                        disabled={line.quantity <= 1 || cartPending}
                        onClick={() => handle(setQuantity(line.variantId, line.quantity - 1))}
                        className="flex h-full w-9 items-center justify-center disabled:text-line"
                      >
                        <Minus className="size-4" aria-hidden="true" />
                      </button>
                      <span className="w-7 text-center text-sm font-semibold" aria-live="polite">
                        {line.quantity}
                      </span>
                      <button
                        type="button"
                        aria-label="Increase quantity"
                        disabled={line.quantity >= limit || cartPending}
                        onClick={() => handle(setQuantity(line.variantId, line.quantity + 1))}
                        className="flex h-full w-9 items-center justify-center disabled:text-line"
                      >
                        <Plus className="size-4" aria-hidden="true" />
                      </button>
                    </div>
                    <p className="font-bold text-ink">{formatXaf(line.unitPrice * line.quantity)}</p>
                  </div>
                  {line.issue ? (
                    <p className="flex items-center gap-1.5 text-xs font-medium text-deal-dark">
                      <AlertTriangle className="size-3.5" aria-hidden="true" />
                      {line.issue}
                    </p>
                  ) : (
                    line.quantity >= limit &&
                    line.availableQuantity <= 10 && (
                      <p className="text-xs text-deal-dark">Only {line.availableQuantity} available</p>
                    )
                  )}
                </div>
                <button
                  type="button"
                  aria-label={`Remove ${line.productName} from cart`}
                  disabled={cartPending}
                  onClick={() => handle(removeFromCart(line.variantId))}
                  className="self-start rounded-md p-1.5 text-muted hover:bg-cream hover:text-ink"
                >
                  <Trash2 className="size-4" aria-hidden="true" />
                </button>
              </li>
            );
          })}
        </ul>
      </div>

      <aside aria-label="Order summary" className="rounded-xl border border-line bg-white p-5">
        <h2 className="text-lg font-bold text-ink">Summary</h2>
        <div className="mt-4 flex justify-between text-sm">
          <span className="text-muted">Subtotal</span>
          <span className="font-bold text-ink">{formatXaf(subtotal)}</span>
        </div>
        <p className="mt-1 text-xs text-muted">
          The delivery fee and final total are calculated at checkout. Stock and prices are
          checked again when you place the order.
        </p>
        {hasIssues && (
          <p className="mt-3 text-xs font-medium text-deal-dark">
            Some items need your attention before checkout.
          </p>
        )}
        <div className="mt-5">
          <Link
            href="/checkout"
            aria-disabled={hasIssues || undefined}
            onClick={(event) => hasIssues && event.preventDefault()}
            className={`flex h-12 w-full items-center justify-center rounded-lg px-6 text-sm font-semibold text-white ${
              hasIssues ? "cursor-not-allowed bg-muted/60" : "bg-ink hover:bg-black"
            }`}
          >
            Proceed to checkout
          </Link>
          {!signedIn && (
            <p className="mt-2 text-center text-xs text-muted">
              You&apos;ll log in or create an account first. Your cart comes with you.
            </p>
          )}
        </div>
      </aside>
    </div>
  );
}
