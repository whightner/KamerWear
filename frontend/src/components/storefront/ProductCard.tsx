import Image from "next/image";
import { Ruler, Star } from "lucide-react";
import type { Product } from "@/types/catalog";
import { discountPercent, formatXaf, sizeHint } from "@/lib/format";
import { FavoriteButton } from "./FavoriteButton";

interface ProductCardProps {
  product: Product;
  /** Value for next/image `sizes`, matching the grid the card sits in. */
  imageSizes: string;
}

export function ProductCard({ product, imageSizes }: ProductCardProps) {
  const discount = discountPercent(product.price, product.oldPrice);

  return (
    <article className="group relative flex h-full flex-col overflow-hidden rounded-xl border border-line bg-white transition hover:-translate-y-0.5 hover:shadow-[0_8px_24px_rgba(27,26,25,0.08)]">
      <div className="relative aspect-[4/5] overflow-hidden bg-[#f3f3f1]">
        <Image
          src={product.image}
          alt={product.imageAlt}
          fill
          sizes={imageSizes}
          className="object-cover transition duration-300 group-hover:scale-[1.03]"
        />
        {discount && (
          <span className="absolute left-2.5 top-2.5 rounded-md bg-deal px-2 py-1 text-xs font-bold text-white">
            -{discount}%
          </span>
        )}
        <div className="absolute right-2.5 top-2.5 z-10">
          <FavoriteButton productName={product.name} />
        </div>
        {product.smartFit && (
          <span className="absolute bottom-2.5 left-2.5 flex items-center gap-1 rounded-md bg-fit px-2 py-1 text-[11px] font-semibold text-white">
            <Ruler className="size-3" aria-hidden="true" />
            Smart Fit
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3.5">
        <p className="text-[11px] font-medium uppercase tracking-wider text-muted">
          {product.department} · {product.category}
        </p>
        <h3 className="truncate text-sm font-semibold text-ink">
          {/* Product pages come later; the link keeps the card keyboard-reachable. */}
          <a
            href="#"
            className="after:absolute after:inset-0 after:content-['']"
          >
            {product.name}
          </a>
        </h3>
        <p className="flex items-center gap-1 text-xs text-muted">
          <Star className="size-3.5 fill-gold text-gold" aria-hidden="true" />
          <span className="font-semibold text-ink">
            {product.rating.toFixed(1)}
          </span>
          <span>({product.reviewCount})</span>
          <span className="sr-only">out of 5 stars</span>
        </p>
        <div className="mt-auto flex flex-wrap items-baseline gap-x-2 pt-1">
          <span
            className={`text-base font-bold ${discount ? "text-deal" : "text-ink"}`}
          >
            {formatXaf(product.price)}
          </span>
          {discount && product.oldPrice && (
            <span className="text-xs text-muted line-through">
              <span className="sr-only">Was </span>
              {formatXaf(product.oldPrice)}
            </span>
          )}
        </div>
        <p className="flex flex-wrap items-center justify-between gap-x-2 text-[11px]">
          <span className="whitespace-nowrap text-muted">
            {sizeHint(product.sizes)}
          </span>
          {product.stockHint && (
            <span className="whitespace-nowrap font-semibold text-deal">
              {product.stockHint}
            </span>
          )}
        </p>
      </div>
    </article>
  );
}
