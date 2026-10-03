import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MessageCircle } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { FormMessage } from "@/components/auth/fields";
import { CancelReturn } from "@/components/returns/CancelReturn";
import { ReturnStatusBadge } from "@/components/returns/ReturnBadges";
import { ReturnHistory } from "@/components/returns/ReturnHistory";
import { ReturnItems } from "@/components/returns/ReturnItems";
import { Container } from "@/components/storefront/Container";
import { returnsApi } from "@/lib/after-sales/api";
import { RETURN_STATUS_HELP } from "@/lib/after-sales/labels";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { formatDateTime } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export async function generateMetadata({ params }: PageProps<"/returns/[returnNumber]">): Promise<Metadata> {
  return { title: `Return ${decodeURIComponent((await params).returnNumber)} — KamerWear` };
}

export default async function ReturnPage({ params, searchParams }: PageProps<"/returns/[returnNumber]">) {
  const { returnNumber } = await params;
  const { created, cancelled } = await searchParams;
  const number = decodeURIComponent(returnNumber);
  await requireUser(`/returns/${returnNumber}`);
  const result = await returnsApi.detail((await getAccessToken()) ?? "", number);
  // Another customer's return looks exactly like a missing one.
  if (!result.ok && result.status === 404) notFound();

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Returns", href: "/account/returns" },
          { label: number },
        ]}
      />
      {!result.ok ? (
        <p role="alert" className="mt-6 rounded-xl border border-line bg-white px-6 py-10 text-center text-ink">
          We couldn&apos;t load this return right now. Please try again in a moment.
        </p>
      ) : (
        <div className="mt-4 max-w-4xl">
          {(created === "1" || cancelled === "1") && (
            <div className="mb-4">
              <FormMessage
                success={
                  created === "1"
                    ? "Return requested. Our team will review it and reply here."
                    : "Your return request was cancelled."
                }
              />
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-3xl font-extrabold tracking-tight text-ink">Return {result.data.return_number}</h1>
            <ReturnStatusBadge status={result.data.status} />
          </div>
          <p className="mt-1 text-sm text-muted">
            For order{" "}
            <Link href={`/orders/${result.data.order_number}`} className="font-semibold text-ink underline underline-offset-2">
              {result.data.order_number}
            </Link>{" "}
            · requested {formatDateTime(result.data.created_at)}
          </p>
          <p className="mt-3 text-sm text-ink">{RETURN_STATUS_HELP[result.data.status]}</p>

          {result.data.refund_note && (
            <div role="note" className="mt-4 rounded-xl border border-gold/50 bg-gold-soft p-4 text-sm text-ink">
              <p className="font-bold">
                Refund recorded: {formatXaf(result.data.refunded_amount ?? result.data.return_value)}
              </p>
              <p className="mt-1">{result.data.refund_note}</p>
            </div>
          )}

          <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_300px]">
            <div className="min-w-0 space-y-6">
              <section aria-labelledby="items-heading" className="rounded-xl border border-line bg-white p-5">
                <h2 id="items-heading" className="text-base font-bold text-ink">Items</h2>
                <ReturnItems items={result.data.items} />
                <p className="mt-2 flex justify-between border-t border-line pt-3 text-sm">
                  <span className="text-muted">Return value (price paid, excluding delivery)</span>
                  <span className="font-bold text-ink">{formatXaf(result.data.return_value)}</span>
                </p>
                {result.data.customer_note && (
                  <p className="mt-3 whitespace-pre-wrap break-words rounded-lg bg-cream p-3 text-sm text-ink">
                    <span className="font-semibold">Your note: </span>
                    {result.data.customer_note}
                  </p>
                )}
              </section>
              <div className="flex flex-wrap items-start gap-3">
                <Link
                  href={`/support/new?return=${encodeURIComponent(result.data.return_number)}`}
                  className="inline-flex h-10 items-center gap-2 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black"
                >
                  <MessageCircle className="size-4" aria-hidden="true" />
                  Contact support about this return
                </Link>
                {result.data.can_cancel && <CancelReturn returnNumber={result.data.return_number} />}
              </div>
            </div>
            <section aria-labelledby="history-heading" className="rounded-xl border border-line bg-white p-5">
              <h2 id="history-heading" className="mb-4 text-base font-bold text-ink">Status history</h2>
              <ReturnHistory events={result.data.history} />
            </section>
          </div>
        </div>
      )}
    </Container>
  );
}
