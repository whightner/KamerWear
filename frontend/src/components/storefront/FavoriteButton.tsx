"use client";

import { useState } from "react";
import { Heart } from "lucide-react";

// Local, per-card state only. Favorites are not saved anywhere yet.
export function FavoriteButton({ productName }: { productName: string }) {
  const [favorite, setFavorite] = useState(false);

  return (
    <button
      type="button"
      aria-pressed={favorite}
      aria-label={
        favorite
          ? `Remove ${productName} from favorites`
          : `Add ${productName} to favorites`
      }
      onClick={() => setFavorite((value) => !value)}
      className="flex size-9 items-center justify-center rounded-full bg-white/95 text-ink shadow-sm transition hover:scale-105"
    >
      <Heart
        className={`size-[18px] ${favorite ? "fill-deal text-deal" : ""}`}
        aria-hidden="true"
      />
    </button>
  );
}
