import "server-only";

import { commerceApi } from "./api";

// A shopper who isn't signed in keeps a temporary cart in the browser. When
// they log in or register, the login form sends its lines (variant id and
// quantity only) and they are merged into the saved cart by the API, which
// combines duplicates, caps at current stock and uses catalog prices.

const MAX_GUEST_LINES = 50;

function parseGuestCart(raw: FormDataEntryValue | null): { variant_id: number; quantity: number }[] {
  if (typeof raw !== "string" || !raw) return [];
  try {
    const value: unknown = JSON.parse(raw);
    if (!Array.isArray(value)) return [];
    return value
      .filter(
        (line): line is { variant_id: number; quantity: number } =>
          typeof line === "object" &&
          line !== null &&
          Number.isInteger(line.variant_id) &&
          Number.isInteger(line.quantity) &&
          line.quantity >= 1 &&
          line.quantity <= 10,
      )
      .slice(0, MAX_GUEST_LINES)
      .map(({ variant_id, quantity }) => ({ variant_id, quantity }));
  } catch {
    return [];
  }
}

/**
 * Merges the guest cart posted with a login/register form.
 * Returns true when some lines couldn't be added in full (or the merge failed).
 */
export async function mergeGuestCart(
  accessToken: string,
  raw: FormDataEntryValue | null,
): Promise<boolean> {
  const items = parseGuestCart(raw);
  if (items.length === 0) return false;
  const result = await commerceApi.mergeCart(accessToken, items);
  return !result.ok || result.data.adjustments.length > 0;
}

/** Adds ?cart=adjusted to a same-site path so the cart notice can be shown. */
export function withCartNotice(path: string): string {
  const url = new URL(path, "http://kamerwear.local");
  url.searchParams.set("cart", "adjusted");
  return url.pathname + url.search;
}
