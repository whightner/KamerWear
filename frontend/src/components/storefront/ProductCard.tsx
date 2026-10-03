import Image from "next/image";
import Link from "next/link";
import { Ruler, Star } from "lucide-react";
import type { Product } from "@/types/catalog";
import { discountPercent, formatXaf, sizeHint } from "@/lib/format";
import {
  primaryImage,
  productHref,
  productLabel,
  stockStatus,
} from "@/lib/products";
import { FavoriteButton } from "./FavoriteButton";

interface ProductCardProps {
  product: Product;
  /** Value for next/image `sizes`, matching the grid the card sits in. */
  imageSizes: string;
}

// Visual priority: image → name → price → discount → rating / Smart Fit / stock.
export function ProductCard({ product, imageSizes }: ProductCardProps) {
  const discount = discountPercent(product.price, product.oldPrice);
  const image = primaryImage(product);
  const stock = stockStatus(product);

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-xl border border-line bg-white transition hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(27,26,25,0.08)]">
      {/* All product photos share the same 4:5 frame and #f2f2f2 background. */}
      <div className="relative aspect-[4/5] overflow-hidden bg-[#f2f2f2]">
        <Image
          src={image.src}
          alt={image.alt}
          fill
          sizes={imageSizes}
          className="object-cover transition duration-300 group-hover:scale-[1.03]"
        />
        <div className="absolute right-2 top-2 z-10">
          <FavoriteButton slug={product.slug} productName={product.name} />
        </div>
      </div>

      <div className="flex flex-1 flex-col p-3">
        <p className="truncate text-[11px] font-medium uppercase tracking-wider text-muted">
          {productLabel(product)}
        </p>
        <h3
          className="mt-1 line-clamp-2 min-h-10 text-sm font-semibold leading-5 text-ink"
          title={product.name}
        >
          <Link
            href={productHref(product)}
            className="after:absolute after:inset-0 after:content-['']"
          >
            {product.name}
          </Link>
        </h3>

        <div className="mt-2">
          <p
            className={`text-base font-bold leading-6 ${discount ? "text-deal" : "text-ink"}`}
          >
            {formatXaf(product.price)}
          </p>
          {/* Reserved line keeps prices aligned whether or not an item is discounted. */}
          <p className="flex h-5 items-center gap-1.5 text-xs">
            {discount && product.oldPrice && (
              <>
                <span className="truncate text-muted line-through">
                  <span className="sr-only">Was </span>
                  {formatXaf(product.oldPrice)}
                </span>
                <span className="shrink-0 rounded bg-deal-soft px-1 font-bold text-deal">
                  -{discount}%
                </span>
              </>
            )}
          </p>
        </div>

        <div className="mt-auto space-y-1 border-t border-line/70 pt-2 text-[11px]">
          <p className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1 text-muted">
              <Star className="size-3 fill-gold text-gold" aria-hidden="true" />
              <span className="font-semibold text-ink">
                {product.rating.toFixed(1)}
              </span>
              <span>({product.reviewCount})</span>
              <span className="sr-only">out of 5 stars</span>
            </span>
            {product.smartFit && (
              <span className="flex shrink-0 items-center gap-1 font-semibold text-fit">
                <Ruler className="size-3" aria-hidden="true" />
                Smart Fit
              </span>
            )}
          </p>
          <p className="flex items-center justify-between gap-2">
            <span className="min-w-0 truncate text-muted">
              {product.sizes.length ? sizeHint(product.sizes) : "One size"}
            </span>
            {stock.kind !== "in" && (
              <span
                className={`shrink-0 font-semibold ${stock.kind === "out" ? "text-muted" : "text-deal"}`}
              >
                {stock.label}
              </span>
            )}
          </p>
        </div>
      </div>
    </article>
  );
}
