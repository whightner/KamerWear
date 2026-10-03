import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";
import { Search } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { OrderTimeline } from "@/components/commerce/OrderTimeline";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { Container } from "@/components/storefront/Container";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { commerceApi } from "@/lib/commerce/api";
import { formatDate } from "@/lib/commerce/labels";

export const metadata: Metadata = { title: "Track order — KamerWear" };

export default async function TrackOrderPage({ searchParams }: PageProps<"/orders/track">) {
  const { number } = await searchParams;
  const query = typeof number === "string" ? number.trim() : "";
  await requireUser(query ? `/orders/track?number=${encodeURIComponent(query)}` : "/orders/track");
  const token = (await getAccessToken()) ?? "";
  const result = query ? await commerceApi.order(token, query) : null;
  const recent = query ? null : await commerceApi.orders(token);

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Track order" }]} />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Track your order</h1>
      <p className="mb-6 mt-1 text-sm text-muted">
        Enter the order number from your confirmation, e.g. KW-2026-7K4M9Q.
      </p>

      <div className="grid gap-6 lg:grid-cols-[420px_1fr] lg:items-start">
        <div className="rounded-xl border border-line bg-white p-5 sm:p-6">
          <Form action="/orders/track" className="space-y-3">
            <label htmlFor="order-number" className="block text-sm font-semibold text-ink">
              Order number
            </label>
            <div className="flex gap-2">
              <input
                id="order-number"
                name="number"
                defaultValue={query}
                required
                autoComplete="off"
                spellCheck={false}
                placeholder="KW-2026-…"
                className="h-11 min-w-0 flex-1 rounded-lg border border-line px-3 text-sm uppercase text-ink outline-none placeholder:normal-case focus:border-ink focus:ring-2 focus:ring-ink/10"
              />
              <button
                type="submit"
                className="flex h-11 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black"
              >
                <Search className="size-4" aria-hidden="true" />
                Track
              </button>
            </div>
          </Form>
          {recent?.ok && recent.data.items.length > 0 && (
            <div className="mt-6 border-t border-line pt-4">
              <h2 className="mb-2 text-sm font-bold text-ink">Your recent orders</h2>
              <ul className="space-y-2 text-sm">
                {recent.data.items.slice(0, 5).map((order) => (
                  <li key={order.order_number} className="flex items-center justify-between gap-2">
                    <Link
                      href={`/orders/track?number=${order.order_number}`}
                      className="font-semibold text-ink underline underline-offset-2"
                    >
                      {order.order_number}
                    </Link>
                    <span className="text-xs text-muted">{formatDate(order.created_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {result && (
          <section aria-live="polite" className="rounded-xl border border-line bg-white p-5 sm:p-6">
            {result.ok ? (
              <>
                <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                  <h2 className="text-lg font-bold text-ink">{result.data.order_number}</h2>
                  <StatusBadge status={result.data.status} />
                </div>
                <OrderTimeline order={result.data} />
                <Link
                  href={`/orders/${result.data.order_number}`}
                  className="mt-5 inline-block text-sm font-semibold text-ink underline underline-offset-2"
                >
                  View order details
                </Link>
              </>
            ) : (
              <p role="alert" className="text-sm text-ink">
                {result.status === 404
                  ? "We couldn't find an order with this number in your account. Check the number and try again."
                  : "We couldn't load tracking right now. Please try again in a moment."}
              </p>
            )}
          </section>
        )}
      </div>
    </Container>
  );
}
