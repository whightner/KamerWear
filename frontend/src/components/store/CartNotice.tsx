"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Info, X } from "lucide-react";
import { Container } from "@/components/storefront/Container";

// Shown after login when some guest-cart items couldn't be added to the saved
// cart in full (sold out, fewer left, or no longer sold). The login action adds
// ?cart=adjusted to the destination in that case.
export function CartNotice() {
  const params = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();
  if (params.get("cart") !== "adjusted") return null;

  function dismiss() {
    const next = new URLSearchParams(params);
    next.delete("cart");
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  return (
    <Container className="pt-4">
      <div
        role="status"
        className="flex items-start gap-3 rounded-lg border border-gold/40 bg-gold-soft px-4 py-3 text-sm text-ink"
      >
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
        <p className="flex-1">
          We added your earlier cart to your account, but some items were sold out or
          limited by current stock.{" "}
          {pathname !== "/cart" && (
            <Link href="/cart" className="font-semibold underline underline-offset-2">
              Review your cart
            </Link>
          )}
        </p>
        <button
          type="button"
          onClick={dismiss}
          aria-label="Dismiss cart message"
          className="rounded-md p-1 hover:bg-white/60"
        >
          <X className="size-4" aria-hidden="true" />
        </button>
      </div>
    </Container>
  );
}
