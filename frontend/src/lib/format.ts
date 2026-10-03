const xafNumber = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });

/** Formats a whole-franc amount, e.g. 28500 -> "28,500 FCFA". */
export function formatXaf(amount: number): string {
  return `${xafNumber.format(amount)} FCFA`;
}

/** Whole-number discount percentage, e.g. (28500, 39900) -> 29. */
export function discountPercent(
  price: number,
  oldPrice?: number,
): number | null {
  if (!oldPrice || oldPrice <= price) return null;
  return Math.round(((oldPrice - price) / oldPrice) * 100);
}

/** Short size hint for cards, e.g. ["S", "M", "L"] -> "Sizes S–L". */
export function sizeHint(sizes: string[]): string {
  if (sizes.length === 0) return "";
  if (sizes.length === 1) return sizes[0];
  return `Sizes ${sizes[0]}–${sizes[sizes.length - 1]}`;
}
