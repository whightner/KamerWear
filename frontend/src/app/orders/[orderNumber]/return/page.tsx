import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ReturnForm } from "@/components/returns/ReturnForm";
import { Container } from "@/components/storefront/Container";
import { returnsApi } from "@/lib/after-sales/api";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { formatDate } from "@/lib/commerce/labels";

export const metadata: Metadata = { title: "Request a return — KamerWear" };

export default async function RequestReturnPage({
  params,
}: PageProps<"/orders/[orderNumber]/return">) {
  const { orderNumber } = await params;
  const number = decodeURIComponent(orderNumber);
  await requireUser(`/orders/${orderNumber}/return`);
  const result = await returnsApi.eligibility((await getAccessToken()) ?? "", number);
  if (!result.ok && result.status === 404) notFound();

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Orders", href: "/orders" },
          { label: number, href: `/orders/${number}` },
          { label: "Return" },
        ]}
      />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Request a return</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Order {number}. Delivered items can be returned within 7 days of delivery.{" "}
        <Link href="/help/returns" className="font-semibold text-ink underline underline-offset-2">
          Return policy
        </Link>
      </p>
      <div className="mt-6 max-w-3xl">
        {!result.ok ? (
          <p role="alert" className="rounded-xl border border-line bg-white px-6 py-10 text-center text-ink">
            We couldn&apos;t load this order right now. Please try again in a moment.
          </p>
        ) : !result.data.eligible ? (
          <div role="status" className="rounded-xl border border-line bg-white p-6">
            <h2 className="text-lg font-bold text-ink">This order can&apos;t be returned</h2>
            <p className="mt-1 text-sm text-ink">{result.data.message}</p>
            {result.data.delivered_at && (
              <p className="mt-1 text-xs text-muted">
                Delivered {formatDate(result.data.delivered_at)}
                {result.data.return_deadline &&
                  ` · return window ended ${formatDate(result.data.return_deadline)}`}
              </p>
            )}
            <div className="mt-4 flex flex-wrap gap-3 text-sm font-semibold">
              <Link href={`/orders/${number}`} className="text-ink underline underline-offset-2">
                Back to the order
              </Link>
              <Link
                href={`/support/new?order=${encodeURIComponent(number)}`}
                className="text-ink underline underline-offset-2"
              >
                Contact support
              </Link>
            </div>
          </div>
        ) : (
          <>
            {result.data.return_deadline && (
              <p className="mb-4 rounded-lg bg-fit-soft px-4 py-2 text-sm text-fit-dark">
                You can request a return until {formatDate(result.data.return_deadline)}.
              </p>
            )}
            <ReturnForm eligibility={result.data} />
          </>
        )}
      </div>
    </Container>
  );
}
