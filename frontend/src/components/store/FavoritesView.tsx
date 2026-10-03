"use client";

import Link from "next/link";
import { ProductCard } from "@/components/storefront/ProductCard";
import { products } from "@/data/products";
import { useStore } from "./StoreProvider";

export function FavoritesView() {
  const { favorites } = useStore();
  const saved = products.filter((product) => favorites.has(product.slug));

  if (saved.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
        <p className="text-lg font-bold text-ink">No favorites yet</p>
        <p className="mt-1 text-sm text-muted">
          Tap the heart on any product to keep it here while you browse.
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
    <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
      {saved.map((product) => (
        <li key={product.slug}>
          <ProductCard
            product={product}
            imageSizes="(min-width: 1024px) 300px, (min-width: 768px) 33vw, 50vw"
          />
        </li>
      ))}
    </ul>
  );
}
