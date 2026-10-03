// Smart Fit API shapes (see backend/app/schemas/fit.py). Photos and pose data
// are never part of them.

export type FitPreference = "slim" | "regular" | "relaxed";
export type FitConfidence = "high" | "medium" | "low";

export interface FitMeasurements {
  shoulder_width_cm: number | null;
  chest_cm: number | null;
  waist_cm: number | null;
  hip_cm: number | null;
  inseam_cm: number | null;
}

export interface FitSuggestedSizes {
  top: string | null;
  bottom: string | null;
}

export interface FitEstimate {
  estimate_id: number;
  height_cm: number;
  fit_preference: FitPreference;
  used_side_photo: boolean;
  measurements: FitMeasurements;
  suggested: FitSuggestedSizes;
  suggested_by_preference: Record<FitPreference, FitSuggestedSizes>;
  size_notes: string[];
  confidence: FitConfidence;
  confidence_factors: string[];
  warnings: string[];
  estimation_version: string;
  size_chart_version: string;
  created_at: string;
}

export interface FitProfile {
  height_cm: number;
  fit_preference: FitPreference;
  top_size: string | null;
  bottom_size: string | null;
  bottom_size_letter: string | null;
  shoe_size_eu: number | null;
  estimated_measurements: FitMeasurements;
  source: "photo_estimate" | "photo_corrected" | "manual";
  confidence: FitConfidence | null;
  estimation_version: string | null;
  confirmed_by_user: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProductFitRecommendation {
  status:
    | "recommended"
    | "unavailable"
    | "not_offered"
    | "missing_size"
    | "no_profile"
    | "unsupported";
  kind: "top" | "bottom" | "shoe" | null;
  size: string | null;
  size_label: string | null;
  nearest_available: string | null;
  source: string | null;
  confidence: FitConfidence | null;
  message: string | null;
}

/** What the product page knows: the API answer, or why there is none. */
export type ProductFitState =
  | ProductFitRecommendation
  | { status: "unsupported" }
  | { status: "signed_out" }
  | { status: "error" };

export interface FitApiError {
  code: string;
  message: string;
  photo?: "front" | "side";
}

// Choices offered in the UI (they match backend/app/fit/size_charts.json;
// the API validates them).
export const TOP_SIZES = ["XS", "S", "M", "L", "XL", "XXL"];
export const BOTTOM_SIZES = ["28", "30", "32", "34", "36", "38", "40"];
export const SHOE_SIZES = Array.from({ length: 14 }, (_, i) => String(35 + i));
export const HEIGHT_MIN = 100;
export const HEIGHT_MAX = 230;

export const PREFERENCES: { value: FitPreference; label: string; hint: string }[] = [
  { value: "slim", label: "Slim", hint: "Closer to the body" },
  { value: "regular", label: "Regular", hint: "Standard fit" },
  { value: "relaxed", label: "Relaxed", hint: "More room" },
];

export const CONFIDENCE_TEXT: Record<FitConfidence, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

export const SOURCE_TEXT: Record<FitProfile["source"], string> = {
  photo_estimate: "Estimated from your photos and confirmed by you",
  photo_corrected: "Estimated from your photos, adjusted and confirmed by you",
  manual: "Entered by you",
};
