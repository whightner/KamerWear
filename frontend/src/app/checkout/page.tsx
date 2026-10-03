import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { CheckoutView } from "@/components/commerce/CheckoutView";
import { Container } from "@/components/storefront/Container";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { commerceApi } from "@/lib/commerce/api";

export const metadata: Metadata = { title: "Checkout — KamerWear" };

export default async function CheckoutPage() {
  const user = await requireUser("/checkout");
  const token = (await getAccessToken()) ?? "";
  const addresses = await commerceApi.addresses(token);
  const defaultAddress = addresses.ok
    ? (addresses.data.find((a) => a.is_default) ?? addresses.data[0])
    : undefined;
  const quote = addresses.ok
    ? await commerceApi.quote(token, defaultAddress?.id ?? null, null)
    : addresses;

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Cart", href: "/cart" },
          { label: "Checkout" },
        ]}
      />
      <h1 className="mb-6 mt-4 text-3xl font-extrabold tracking-tight text-ink">Checkout</h1>

      {!addresses.ok || !quote.ok ? (
        <p role="alert" className="rounded-xl border border-line bg-white px-6 py-16 text-center text-ink">
          We couldn&apos;t load checkout right now. Nothing has been ordered. Please try again in
          a moment.
        </p>
      ) : quote.data.items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
          <p className="text-lg font-bold text-ink">Your cart is empty.</p>
          <p className="mt-1 text-sm text-muted">Add something you like, then come back to check out.</p>
          <Link
            href="/shop"
            className="mt-5 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
          >
            Browse the shop
          </Link>
        </div>
      ) : (
        <CheckoutView
          addresses={addresses.data}
          initialQuote={quote.data}
          // One key per visit to checkout: repeating "Place order" can't create a second order.
          idempotencyKey={crypto.randomUUID()}
          addressDefaults={{
            recipient_name: `${user.profile.first_name} ${user.profile.last_name}`,
            phone: user.profile.phone ?? "",
          }}
        />
      )}
    </Container>
  );
}
