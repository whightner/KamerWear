"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Minus, Plus, ScanSearch, ShoppingBag, Star, Zap } from "lucide-react";
import type {
  ProductDetail as ApiProduct,
  ProductImage,
  ProductListItem,
  ProductVariant,
} from "@/lib/api/types";
import {
  maxQuantity,
  useCartQuantity,
  useStore,
} from "@/components/store/StoreProvider";
import { DeliveryCityButton } from "@/components/storefront/DeliveryCityButton";
import { FavoriteButton } from "@/components/storefront/FavoriteButton";
import { ProductCard } from "@/components/storefront/ProductCard";
import { formatXaf } from "@/lib/format";
import {
  isShoe as isShoeProduct,
  productHref,
  productLabel,
  stockStatus,
} from "@/lib/products";
import { ProductGallery } from "./ProductGallery";
import { SmartFitBlock } from "./SmartFitBlock";

interface ProductDetailProps {
  product: ApiProduct;
  /** From GET /products/{slug}/similar; null if that request failed. */
  similar: ProductListItem[] | null;
}

/** Photos for a colour, falling back to colour-neutral photos, then all photos. */
function galleryFor(images: ProductImage[], colorName: string): ProductImage[] {
  const forColor = images.filter((image) => image.color_name === colorName);
  if (forColor.length) return forColor;
  const general = images.filter((image) => image.color_name === null);
  return general.length ? general : images;
}

export function ProductDetail({ product, similar }: ProductDetailProps) {
  const router = useRouter();
  const { addToCart, cartPending } = useStore();
  const [colorName, setColorName] = useState(product.colors[0]?.name ?? "");
  const [imageIndex, setImageIndex] = useState(0);
  const [size, setSize] = useState<string>();
  const [quantity, setQuantity] = useState(1);
  const [sizeError, setSizeError] = useState(false);
  const [confirmation, setConfirmation] = useState("");
  const [cartError, setCartError] = useState("");
  const [showSimilar, setShowSimilar] = useState(false);
  const similarRef = useRef<HTMLElement>(null);
  const sizeGroupRef = useRef<HTMLFieldSetElement>(null);

  const isShoe = isShoeProduct(product);
  const needsSize = product.sizes.length > 0;
  const gallery = galleryFor(product.images, colorName);
  const colorHex =
    product.colors.find((c) => c.name === colorName)?.hex ?? "#cccccc";

  // product + colour + size → the real backend variant.
  const variantsForColor = product.variants.filter(
    (v) => v.color_name === colorName,
  );
  const variantFor = (sizeValue: string | null): ProductVariant | undefined =>
    variantsForColor.find((v) => v.size === sizeValue);
  const selected = needsSize
    ? size
      ? variantFor(size)
      : undefined
    : variantFor(null);
  const colorAvailable = variantsForColor.reduce(
    (sum, v) => sum + v.available_quantity,
    0,
  );

  // Stock comes from the API; the quantity can't exceed what is left after
  // what's already in the cart.
  const inCart = useCartQuantity(selected?.id);
  const remaining = selected
    ? Math.max(0, maxQuantity(selected.available_quantity) - inCart)
    : 0;
  const quantityLimit = Math.max(1, remaining);
  const effectiveQuantity = Math.min(quantity, quantityLimit);
  const stock = stockStatus(
    selected ? selected.available_quantity : colorAvailable,
  );
  const canBuy = selected ? remaining > 0 : colorAvailable > 0;

  // A variant price override replaces the product price (and its discount).
  const hasOverride =
    selected !== undefined && selected.price !== product.price;
  const price = selected?.price ?? product.price;
  const discount = hasOverride ? null : product.discount_percent;

  const soldOutSizes = product.sizes.filter((s) => !variantFor(s)?.in_stock);

  useEffect(() => {
    if (showSimilar) {
      similarRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    }
  }, [showSimilar]);

  function selectColor(name: string) {
    setColorName(name);
    setImageIndex(0);
    // Keep the chosen size only if it is still available in the new colour.
    const keep = size
      ? product.variants.find((v) => v.color_name === name && v.size === size)
      : undefined;
    if (!keep?.in_stock) setSize(undefined);
  }

  function selectSize(value: string) {
    setSize(value);
    setSizeError(false);
  }

  /** Adds the selected variant to the cart; resolves false if nothing was added. */
  async function addSelection(): Promise<boolean> {
    if (needsSize && !size) {
      setSizeError(true);
      sizeGroupRef.current
        ?.querySelector<HTMLButtonElement>("button:enabled")
        ?.focus();
      return false;
    }
    if (!selected || remaining <= 0) return false;
    const image = gallery[0];
    setConfirmation("");
    setCartError("");
    const result = await addToCart({
      variantId: selected.id,
      sku: selected.sku,
      productId: product.id,
      productSlug: product.slug,
      productName: product.name,
      categorySlug: product.category.slug,
      colorName: selected.color_name,
      size: selected.size,
      unitPrice: selected.price,
      image: image ? { src: image.image_path, alt: image.alt_text } : null,
      availableQuantity: selected.available_quantity,
      quantity: effectiveQuantity,
    });
    if (!result.ok) {
      if (result.code === "session_expired") {
        router.push(`/login?next=${encodeURIComponent(productHref(product))}&reason=expired`);
      } else {
        setCartError(result.message);
      }
      return false;
    }
    const parts = [
      selected.color_name,
      selected.size && (isShoe ? `EU ${selected.size}` : selected.size),
    ].filter(Boolean);
    setConfirmation(
      `Added to cart: ${product.name} (${parts.join(", ")}) × ${effectiveQuantity}.`,
    );
    setQuantity(1);
    return true;
  }

  async function buyNow() {
    // Buy Now adds the item and goes to checkout (guests log in first; their
    // cart is merged into their account).
    if (await addSelection()) router.push("/checkout");
  }

  return (
    <>
      <div className="grid gap-8 lg:grid-cols-12 lg:gap-12">
        <div className="lg:col-span-7">
          <ProductGallery
            images={gallery}
            selected={imageIndex}
            onSelect={setImageIndex}
          />
        </div>

        <div className="lg:col-span-5">
          <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted">
            {productLabel(product)}
            {product.is_new && (
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
              {product.rating_average.toFixed(1)}
            </span>
            <span className="sr-only">out of 5 stars,</span>
            <span>· {product.review_count} reviews</span>
          </a>

          <div className="mt-4">
            <p
              className={`text-3xl font-extrabold ${discount ? "text-deal" : "text-ink"}`}
            >
              {formatXaf(price)}
            </p>
            {discount && product.compare_at_price && (
              <p className="mt-1 flex items-center gap-2 text-sm">
                <span className="text-muted line-through">
                  <span className="sr-only">Was </span>
                  {formatXaf(product.compare_at_price)}
                </span>
                <span className="rounded bg-deal-soft px-1.5 py-0.5 text-xs font-bold text-deal">
                  -{discount}%
                </span>
              </p>
            )}
          </div>

          <div className="mt-6 space-y-5">
            {product.smart_fit && (
              <SmartFitBlock
                isShoe={isShoe}
                demoSize={product.smart_fit_demo_size ?? undefined}
                canSelect={
                  !!product.smart_fit_demo_size &&
                  !!variantFor(product.smart_fit_demo_size)?.in_stock
                }
                onSelectSize={selectSize}
              />
            )}

            <fieldset>
              <legend className="text-sm font-semibold text-ink">
                Color: <span className="font-normal">{colorName}</span>
              </legend>
              {product.colors.length > 1 ? (
                <div className="mt-2 flex flex-wrap gap-2">
                  {product.colors.map((option) => {
                    const colorSoldOut = !product.variants.some(
                      (v) => v.color_name === option.name && v.in_stock,
                    );
                    return (
                      <button
                        key={option.name}
                        type="button"
                        aria-label={
                          colorSoldOut
                            ? `${option.name}, sold out`
                            : option.name
                        }
                        aria-pressed={option.name === colorName}
                        title={option.name}
                        onClick={() => selectColor(option.name)}
                        className={`flex size-10 items-center justify-center rounded-full border-2 ${
                          option.name === colorName
                            ? "border-ink"
                            : "border-transparent hover:border-line"
                        } ${colorSoldOut ? "opacity-40" : ""}`}
                      >
                        <span
                          className="size-7 rounded-full ring-1 ring-black/10"
                          style={{ backgroundColor: option.hex }}
                        />
                      </button>
                    );
                  })}
                </div>
              ) : (
                <p className="mt-2 flex items-center gap-2 text-sm text-muted">
                  <span
                    className="size-5 rounded-full ring-1 ring-black/10"
                    style={{ backgroundColor: colorHex }}
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
                    const unavailable = !variantFor(option)?.in_stock;
                    const isSelected = option === size;
                    return (
                      <button
                        key={option}
                        type="button"
                        disabled={unavailable}
                        aria-pressed={isSelected}
                        aria-label={
                          unavailable ? `${option}, sold out` : option
                        }
                        onClick={() => selectSize(option)}
                        className={`h-11 min-w-12 rounded-lg border px-3 text-sm font-semibold transition ${
                          isSelected
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
              className={`flex flex-wrap items-center gap-2 text-sm font-semibold ${
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
              {needsSize && !selected && colorAvailable > 0 && (
                <span className="font-normal text-muted">
                  · Choose a size to check its stock
                </span>
              )}
              {!selected && soldOutSizes.length > 0 && colorAvailable > 0 && (
                <span className="font-normal text-muted">
                  · Size {soldOutSizes.join(", ")} sold out in {colorName}
                </span>
              )}
            </p>

            {selected && inCart > 0 && (
              <p className="text-xs text-muted">
                {remaining > 0
                  ? `${inCart} already in your cart. You can add ${remaining} more.`
                  : `All available stock of this item (${inCart}) is already in your cart.`}
              </p>
            )}

            {canBuy && (
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
                    disabled={effectiveQuantity <= 1}
                    onClick={() =>
                      setQuantity(Math.max(1, effectiveQuantity - 1))
                    }
                    className="flex h-full w-10 items-center justify-center disabled:text-line"
                  >
                    <Minus className="size-4" aria-hidden="true" />
                  </button>
                  <span
                    className="w-8 text-center text-sm font-semibold"
                    aria-live="polite"
                    data-testid="quantity"
                  >
                    {effectiveQuantity}
                  </span>
                  <button
                    type="button"
                    aria-label="Increase quantity"
                    disabled={!selected || effectiveQuantity >= quantityLimit}
                    onClick={() =>
                      setQuantity(
                        Math.min(quantityLimit, effectiveQuantity + 1),
                      )
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
                disabled={!canBuy || cartPending}
                aria-busy={cartPending}
                className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-ink text-sm font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-muted/50"
              >
                <ShoppingBag className="size-4" aria-hidden="true" />
                {canBuy
                  ? "Add to Cart"
                  : stock.kind === "out"
                    ? "Out of stock"
                    : "In your cart"}
              </button>
              <div className="grid grid-cols-[1fr_auto] gap-3">
                <button
                  type="button"
                  onClick={buyNow}
                  disabled={!canBuy || cartPending}
                  className="flex h-12 items-center justify-center gap-2 rounded-lg bg-deal text-sm font-semibold text-white hover:bg-deal-dark disabled:cursor-not-allowed disabled:bg-muted/50"
                >
                  <Zap className="size-4" aria-hidden="true" />
                  Buy Now
                </button>
                <FavoriteButton product={product} variant="labelled" />
              </div>
              {cartError && (
                <p role="alert" className="text-sm font-medium text-deal-dark">
                  {cartError}
                </p>
              )}
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
            Demo: rule-based matching by product type. Image-based matching
            comes later.
          </p>
          {similar === null ? (
            <p className="mt-5 text-sm text-ink" role="alert">
              We couldn&apos;t load similar items right now. Please try again
              later.
            </p>
          ) : similar.length > 0 ? (
            <ul className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-4">
              {similar.map((item) => (
                <li key={item.id}>
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
