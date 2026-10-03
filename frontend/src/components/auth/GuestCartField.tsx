"use client";

import { useStore } from "@/components/store/StoreProvider";

/**
 * Sends the guest cart (variant ids and quantities only) with the login or
 * register form, so it can be merged into the saved cart. Prices are never sent.
 */
export function GuestCartField() {
  const { cart, signedIn } = useStore();
  if (signedIn || cart.length === 0) return null;
  const lines = cart.map((line) => ({ variant_id: line.variantId, quantity: line.quantity }));
  return <input type="hidden" name="guest_cart" value={JSON.stringify(lines)} />;
}
