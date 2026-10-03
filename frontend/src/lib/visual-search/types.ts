// Visual search API responses (backend/app/schemas/visual_search.py).

import type { ProductListItem } from "@/lib/api/types";

export interface VisualSearchItem {
  product: ProductListItem;
  /** Cosine similarity of the best-matching photo. For ranking/debugging only. */
  similarity_score: number;
  matched_image: string;
  /** true/false when the type guard was applied, otherwise null. */
  matches_predicted_type: boolean | null;
}

export interface VisualSearchResponse {
  query: {
    predicted_type: string | null;
    predicted_type_label: string | null;
    type_guard_applied: boolean;
    weak_matches: boolean;
    model: string;
    search_ms: number;
  };
  items: VisualSearchItem[];
}

export interface VisualSimilarResponse {
  type_guard_applied: boolean;
  weak_matches: boolean;
  model: string;
  items: VisualSearchItem[];
}

export type VisualSimilarResult =
  | { ok: true; data: VisualSimilarResponse }
  | { ok: false; code: string };
