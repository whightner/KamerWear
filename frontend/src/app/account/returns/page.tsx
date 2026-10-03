import type { Metadata } from "next";
import Link from "next/link";
import { RotateCcw } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ReturnStatusBadge } from "@/components/returns/ReturnBadges";
import { Container } from "@/components/storefront/Container";
import { returnsApi } from "@/lib/after-sales/api";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { formatDate } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export const metadata: Metadata = { title: "My returns — KamerWear" };

export default async function ReturnsPage() {
  await requireUser("/account/returns");
  const result = await returnsApi.list((await getAccessToken()) ?? "", { limit: 50 });

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[{ label: "Home", href: "/" }, { label: "My account", href: "/account" }, { label: "Returns" }]}
      />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">My returns</h1>
      <p className="mt-1 text-sm text-muted">
        Start a return from a delivered order.{" "}
        <Link href="/help/returns" className="font-semibold text-ink underline underline-offset-2">
          How returns work
        </Link>
      </p>
      <div className="mt-6 max-w-4xl">
        {!result.ok ? (
          <p role="alert" className="rounded-xl border border-line bg-white px-6 py-10 text-center text-ink">
            We couldn&apos;t load your returns right now. Please try again in a moment.
          </p>
        ) : result.data.items.length === 0 ? (
          <div className="rounded-xl border border-line bg-white px-6 py-12 text-center">
            <RotateCcw className="mx-auto size-8 text-muted" aria-hidden="true" />
            <p className="mt-2 font-semibold text-ink">No returns yet</p>
            <p className="mt-1 text-sm text-muted">Delivered orders show a “Request a return” button.</p>
            <Link href="/orders" className="mt-4 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white">
              View my orders
            </Link>
          </div>
        ) : (
          <ul className="space-y-3">
            {result.data.items.map((item) => (
              <li key={item.return_number}>
                <Link
                  href={`/returns/${item.return_number}`}
                  className="grid gap-2 rounded-xl border border-line bg-white p-4 hover:border-ink sm:grid-cols-[1fr_auto] sm:items-center"
                >
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-ink">{item.return_number}</span>
                      <ReturnStatusBadge status={item.status} />
                    </span>
                    <span className="mt-1 block text-sm text-muted">
                      Order {item.order_number} · {formatDate(item.created_at)} · {item.item_count}{" "}
                      {item.item_count === 1 ? "item" : "items"} · {item.reason_summary}
                    </span>
                  </span>
                  <span className="text-sm font-semibold text-ink sm:text-right">
                    <span className="sr-only">Return value: </span>
                    {formatXaf(item.return_value)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </Container>
  );
}
