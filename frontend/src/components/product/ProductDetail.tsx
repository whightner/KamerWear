"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Minus, Plus, ScanSearch, ShoppingBag, Star, Zap } from "lucide-react";
import type { Product } from "@/types/catalog";
import { useStore } from "@/components/store/StoreProvider";
import { DeliveryCityButton } from "@/components/storefront/DeliveryCityButton";
import { FavoriteButton } from "@/components/storefront/FavoriteButton";
import { ProductCard } from "@/components/storefront/ProductCard";
import { discountPercent, formatXaf } from "@/lib/format";
import { productLabel, stockStatus } from "@/lib/products";
import { ProductGallery } from "./ProductGallery";
import { SmartFitBlock } from "./SmartFitBlock";

interface ProductDetailProps {
  product: Product;
  similar: Product[];
}

export function ProductDetail({ product, similar }: ProductDetailProps) {
  const router = useRouter();
  const { addToCart } = useStore();
  const [colorIndex, setColorIndex] = useState(0);
  const [imageIndex, setImageIndex] = useState(0);
  const [size, setSize] = useState<string>();
  const [quantity, setQuantity] = useState(1);
  const [sizeError, setSizeError] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [showSimilar, setShowSimilar] = useState(false);
  const similarRef = useRef<HTMLElement>(null);
  const sizeGroupRef = useRef<HTMLFieldSetElement>(null);

  const color = product.colors[colorIndex];
  const discount = discountPercent(product.price, product.oldPrice);
  const stock = stockStatus(product);
  const isShoe = product.category === "shoes";
  const needsSize = product.sizes.length > 0;
  const soldOut = new Set(product.soldOutSizes ?? []);
  const maxQuantity = Math.max(1, Math.min(10, product.stock));

  useEffect(() => {
    if (showSimilar) {
      similarRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [showSimilar]);

  function selectSize(value: string) {
    setSize(value);
    setSizeError(false);
  }

  /** Adds the current selection to the cart; returns false if a size is missing. */
  function addSelection(): boolean {
    if (needsSize && !size) {
      setSizeError(true);
      sizeGroupRef.current
        ?.querySelector<HTMLButtonElement>("button:enabled")
        ?.focus();
      return false;
    }
    addToCart({ slug: product.slug, colorSlug: color.slug, size, quantity });
    const parts = [color.name, size && (isShoe ? `EU ${size}` : size)].filter(
      Boolean,
    );
    setConfirmation(
      `Added to cart: ${product.name} (${parts.join(", ")}) × ${quantity}.`,
    );
    return true;
  }

  function buyNow() {
    // No checkout yet: Buy Now adds the item and opens the cart.
    if (addSelection()) router.push("/cart");
  }

  return (
    <>
      <div className="grid gap-8 lg:grid-cols-12 lg:gap-12">
        <div className="lg:col-span-7">
          <ProductGallery
            images={color.images}
            selected={imageIndex}
            onSelect={setImageIndex}
          />
        </div>

        <div className="lg:col-span-5">
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted">
            {productLabel(product)}
            {product.isNew && (
              <span className="rounded bg-gold-soft px-1.5 py-0.5 text-[10px] font-bold text-ink">
                NEW
              </span>
            )}
          </p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-ink">
            {product.name}
          </h1>

          <a
            href="#reviews"
            className="mt-2 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink"
          >
            <Star className="size-4 fill-gold text-gold" aria-hidden="true" />
            <span className="font-semibold text-ink">
              {product.rating.toFixed(1)}
            </span>
            <span className="sr-only">out of 5 stars,</span>
            <span>· {product.reviewCount} reviews</span>
          </a>

          <div className="mt-4">
            <p
              className={`text-3xl font-extrabold ${discount ? "text-deal" : "text-ink"}`}
            >
              {formatXaf(product.price)}
            </p>
            {discount && product.oldPrice && (
              <p className="mt-1 flex items-center gap-2 text-sm">
                <span className="text-muted line-through">
                  <span className="sr-only">Was </span>
                  {formatXaf(product.oldPrice)}
                </span>
                <span className="rounded bg-deal-soft px-1.5 py-0.5 text-xs font-bold text-deal">
                  -{discount}%
                </span>
              </p>
            )}
          </div>

          <div className="mt-6 space-y-5">
            {product.smartFit && (
              <SmartFitBlock
                isShoe={isShoe}
                demoSize={product.smartFitDemoSize}
                canSelect={
                  !!product.smartFitDemoSize &&
                  !soldOut.has(product.smartFitDemoSize) &&
                  stock.kind !== "out"
                }
                onSelectSize={selectSize}
              />
            )}

            <fieldset>
              <legend className="text-sm font-semibold text-ink">
                Color: <span className="font-normal">{color.name}</span>
              </legend>
              {product.colors.length > 1 ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {product.colors.map((option, index) => (
                    <button
                      key={option.slug}
                      type="button"
                      aria-label={option.name}
                      aria-pressed={index === colorIndex}
                      title={option.name}
                      onClick={() => {
                        setColorIndex(index);
                        setImageIndex(0);
                      }}
                      className={`flex size-10 items-center justify-center rounded-full border-2 ${
                        index === colorIndex
                          ? "border-ink"
                          : "border-transparent hover:border-line"
                      }`}
                    >
                      <span
                        className="size-7 rounded-full ring-1 ring-black/10"
                        style={{ backgroundColor: option.swatch }}
                      />
                    </button>
                  ))}
                </div>
              ) : (
                <p className="mt-2 flex items-center gap-2 text-sm text-muted">
                  <span
                    className="size-5 rounded-full ring-1 ring-black/10"
                    style={{ backgroundColor: color.swatch }}
                    aria-hidden="true"
                  />
                  Available in one colour
                </p>
              )}
            </fieldset>

            <fieldset ref={sizeGroupRef}>
              <legend className="text-sm font-semibold text-ink">
                {needsSize ? (isShoe ? "Size (EU)" : "Size") : "Size: "}
                {!needsSize && <span className="font-normal">One size</span>}
              </legend>
              {needsSize && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {product.sizes.map((option) => {
                    const unavailable =
                      soldOut.has(option) || stock.kind === "out";
                    const selected = option === size;
                    return (
                      <button
                        key={option}
                        type="button"
                        disabled={unavailable}
                        aria-pressed={selected}
                        aria-label={
                          unavailable ? `${option}, sold out` : option
                        }
                        onClick={() => selectSize(option)}
                        className={`h-11 min-w-12 rounded-lg border px-3 text-sm font-semibold transition ${
                          selected
                            ? "border-ink bg-ink text-white"
                            : unavailable
                              ? "cursor-not-allowed border-line bg-cream/60 text-muted line-through"
                              : "border-line bg-white text-ink hover:border-ink"
                        }`}
                      >
                        {option}
                      </button>
                    );
                  })}
                </div>
              )}
              {sizeError && (
                <p
                  role="alert"
                  className="mt-2 text-sm font-semibold text-deal"
                >
                  Please choose a size first.
                </p>
              )}
            </fieldset>

            <p
              className={`flex items-center gap-2 text-sm font-semibold ${
                stock.kind === "in"
                  ? "text-fit"
                  : stock.kind === "low"
                    ? "text-deal"
                    : "text-muted"
              }`}
            >
              <span
                className={`size-2 rounded-full ${
                  stock.kind === "in"
                    ? "bg-fit"
                    : stock.kind === "low"
                      ? "bg-deal"
                      : "bg-muted"
                }`}
                aria-hidden="true"
              />
              {stock.label}
              {soldOut.size > 0 && stock.kind !== "out" && (
                <span className="font-normal text-muted">
                  · Size {[...soldOut].join(", ")} sold out
                </span>
              )}
            </p>

            {stock.kind !== "out" && (
              <div className="flex items-center gap-3">
                <span
                  id="quantity-label"
                  className="text-sm font-semibold text-ink"
                >
                  Quantity
                </span>
                <div
                  role="group"
                  aria-labelledby="quantity-label"
                  className="flex h-10 items-center rounded-lg border border-line bg-white"
                >
                  <button
                    type="button"
                    aria-label="Decrease quantity"
                    disabled={quantity <= 1}
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    className="flex h-full w-10 items-center justify-center disabled:text-line"
                  >
                    <Minus className="size-4" aria-hidden="true" />
                  </button>
                  <span
                    className="w-8 text-center text-sm font-semibold"
                    aria-live="polite"
                  >
                    {quantity}
                  </span>
                  <button
                    type="button"
                    aria-label="Increase quantity"
                    disabled={quantity >= maxQuantity}
                    onClick={() =>
                      setQuantity((q) => Math.min(maxQuantity, q + 1))
                    }
                    className="flex h-full w-10 items-center justify-center disabled:text-line"
                  >
                    <Plus className="size-4" aria-hidden="true" />
                  </button>
                </div>
              </div>
            )}

            <div className="space-y-3">
              <button
                type="button"
                onClick={addSelection}
                disabled={stock.kind === "out"}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-ink text-sm font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-muted/50"
              >
                <ShoppingBag className="size-4" aria-hidden="true" />
                {stock.kind === "out" ? "Out of stock" : "Add to Cart"}
              </button>
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <button
                  type="button"
                  onClick={buyNow}
                  disabled={stock.kind === "out"}
                  className="flex h-12 items-center justify-center gap-2 rounded-lg bg-deal text-sm font-semibold text-white hover:bg-deal-dark disabled:cursor-not-allowed disabled:bg-muted/50"
                >
                  <Zap className="size-4" aria-hidden="true" />
                  Buy Now
                </button>
                <FavoriteButton
                  slug={product.slug}
                  productName={product.name}
                  variant="labelled"
                />
              </div>
              <p role="status" className="min-h-5 text-sm text-fit-dark">
                {confirmation && (
                  <>
                    {confirmation}{" "}
                    <Link
                      href="/cart"
                      className="font-semibold underline underline-offset-2"
                    >
                      View cart
                    </Link>
                  </>
                )}
              </p>
            </div>

            <button
              type="button"
              aria-expanded={showSimilar}
              aria-controls="similar-products"
              onClick={() => setShowSimilar((value) => !value)}
              className="flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-ink/80 text-sm font-semibold text-ink hover:bg-cream"
            >
              <ScanSearch className="size-4" aria-hidden="true" />
              {showSimilar ? "Hide similar items" : "Find Similar"}
            </button>

            <div className="rounded-xl border border-line bg-white p-4 text-sm">
              <DeliveryCityButton className="flex" />
              <p className="mt-3 font-semibold text-ink">
                Estimated delivery: 1–3 days
              </p>
              <p className="mt-0.5 text-xs text-muted">
                Demo estimate for Douala, not a guarantee. Fees and final timing
                are shown at checkout.
              </p>
            </div>
          </div>
        </div>
      </div>

      {showSimilar && (
        <section
          id="similar-products"
          ref={similarRef}
          aria-labelledby="similar-heading"
          className="mt-12 scroll-mt-32 rounded-2xl border border-line bg-white p-6"
        >
          <h2
            id="similar-heading"
            className="flex items-center gap-2 text-xl font-extrabold text-ink"
          >
            <ScanSearch className="size-5" aria-hidden="true" />
            Similar to {product.name}
          </h2>
          <p className="mt-1 text-sm text-muted">
            Demo: matched by product type. Image-based matching comes later.
          </p>
          {similar.length > 0 ? (
            <ul className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
              {similar.map((item) => (
                <li key={item.slug}>
                  <ProductCard
                    product={item}
                    imageSizes="(min-width: 768px) 25vw, 50vw"
                  />
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm text-ink">
              No similar items in the catalog yet.{" "}
              <Link
                href="/shop"
                className="font-semibold underline underline-offset-2"
              >
                Browse the shop
              </Link>
            </p>
          )}
        </section>
      )}
    </>
  );
}
