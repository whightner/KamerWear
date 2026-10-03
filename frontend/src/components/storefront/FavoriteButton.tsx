"use client";

import { Heart } from "lucide-react";
import { useStore } from "@/components/store/StoreProvider";

interface FavoriteButtonProps {
  slug: string;
  productName: string;
  /** "icon" for cards, "labelled" for the product page. */
  variant?: "icon" | "labelled";
}

// Favorites are shared across cards and the product page, but only kept in
// memory for this browser session (no account persistence yet).
export function FavoriteButton({
  slug,
  productName,
  variant = "icon",
}: FavoriteButtonProps) {
  const { isFavorite, toggleFavorite } = useStore();
  const favorite = isFavorite(slug);
  const label = favorite
    ? `Remove ${productName} from favorites`
    : `Add ${productName} to favorites`;
  const heart = (
    <Heart
      className={`size-4 ${favorite ? "fill-deal text-deal" : ""}`}
      aria-hidden="true"
    />
  );

  if (variant === "labelled") {
    return (
      <button
        type="button"
        aria-pressed={favorite}
        aria-label={label}
        onClick={() => toggleFavorite(slug)}
        className="inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-ink/40"
      >
        {heart}
        {favorite ? "Saved" : "Save"}
      </button>
    );
  }

  return (
    <button
      type="button"
      aria-pressed={favorite}
      aria-label={label}
      onClick={() => toggleFavorite(slug)}
      className="flex size-8 items-center justify-center rounded-full bg-white text-ink shadow-sm ring-1 ring-black/5 transition hover:scale-105"
    >
      {heart}
    </button>
  );
}
