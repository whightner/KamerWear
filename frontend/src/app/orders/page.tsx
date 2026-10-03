import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight, Package } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { Container } from "@/components/storefront/Container";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { commerceApi } from "@/lib/commerce/api";
import { formatDate, paymentStatusLabel } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export const metadata: Metadata = { title: "My orders — KamerWear" };

export default async function OrdersPage() {
  await requireUser("/orders");
  const result = await commerceApi.orders((await getAccessToken()) ?? "");

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "My account", href: "/account" },
          { label: "Orders" },
        ]}
      />
      <div className="mb-6 mt-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">My orders</h1>
          <p className="mt-1 text-sm text-muted">Newest first.</p>
        </div>
        <Link href="/orders/track" className="text-sm font-semibold text-ink underline underline-offset-2">
          Track an order
        </Link>
      </div>

      {!result.ok ? (
        <p role="alert" className="rounded-xl border border-line bg-white px-6 py-16 text-center text-ink">
          We couldn&apos;t load your orders right now. Please try again in a moment.
        </p>
      ) : result.data.items.length === 0 ? (
        <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
          <Package className="mx-auto size-8 text-muted" aria-hidden="true" />
          <p className="mt-3 text-lg font-bold text-ink">No orders yet</p>
          <p className="mt-1 text-sm text-muted">When you place an order, it will appear here.</p>
          <Link
            href="/shop"
            className="mt-5 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
          >
            Browse the shop
          </Link>
        </div>
      ) : (
        <ul className="divide-y divide-line rounded-xl border border-line bg-white">
          {result.data.items.map((order) => (
            <li key={order.order_number}>
              <Link
                href={`/orders/${order.order_number}`}
                className="flex flex-wrap items-center gap-x-6 gap-y-2 p-4 hover:bg-cream/50 sm:p-5"
              >
                <div className="min-w-0 flex-1 basis-48">
                  <p className="font-bold text-ink">{order.order_number}</p>
                  <p className="text-sm text-muted">
                    {formatDate(order.created_at)} · {order.item_count}{" "}
                    {order.item_count === 1 ? "item" : "items"}
                  </p>
                </div>
                <div className="basis-40">
                  <StatusBadge status={order.status} />
                  <p className="mt-1 text-xs text-muted">
                    {paymentStatusLabel(order.payment_status, order.payment_method)}
                  </p>
                </div>
                <p className="font-bold text-ink">{formatXaf(order.total)}</p>
                <ChevronRight className="size-4 text-muted" aria-hidden="true" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Container>
  );
}
