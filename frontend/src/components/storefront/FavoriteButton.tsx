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
      className="flex size-8 items-center justify-center rounded-full bg-white text-ink shadow-sm ring-1 ring-black/5 transition hover:scale-105"
    >
      <Heart
        className={`size-4 ${favorite ? "fill-deal text-deal" : ""}`}
        aria-hidden="true"
      />
    </button>
  );
}
