import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { OrderView } from "@/components/commerce/OrderView";
import { Container } from "@/components/storefront/Container";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { commerceApi } from "@/lib/commerce/api";
import { formatDateTime } from "@/lib/commerce/labels";

export async function generateMetadata({
  params,
}: PageProps<"/orders/[orderNumber]">): Promise<Metadata> {
  const { orderNumber } = await params;
  return { title: `Order ${decodeURIComponent(orderNumber)} — KamerWear` };
}

export default async function OrderPage({
  params,
  searchParams,
}: PageProps<"/orders/[orderNumber]">) {
  const { orderNumber } = await params;
  const { placed } = await searchParams;
  const number = decodeURIComponent(orderNumber);
  await requireUser(`/orders/${orderNumber}`);
  const result = await commerceApi.order((await getAccessToken()) ?? "", number);
  // Another customer's order looks exactly like a missing one.
  if (!result.ok && result.status === 404) notFound();

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Orders", href: "/orders" },
          { label: number },
        ]}
      />
      {!result.ok ? (
        <p role="alert" className="mt-6 rounded-xl border border-line bg-white px-6 py-16 text-center text-ink">
          We couldn&apos;t load this order right now. Please try again in a moment.
        </p>
      ) : (
        <>
          {placed === "1" && (
            <div
              role="status"
              className="mt-4 flex items-start gap-3 rounded-xl border border-fit/30 bg-fit-soft p-4 text-fit-dark"
            >
              <CheckCircle2 className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
              <div>
                <p className="font-bold">Order placed</p>
                <p className="text-sm">
                  Thank you! Keep your order number {result.data.order_number} to track your
                  delivery.
                  {result.data.payment_method !== "cash_on_delivery" &&
                    " This was a demo payment: no money has been taken."}
                </p>
              </div>
            </div>
          )}
          <h1 className="mb-1 mt-4 text-3xl font-extrabold tracking-tight text-ink">
            Order {result.data.order_number}
          </h1>
          <p className="mb-6 text-sm text-muted">Placed {formatDateTime(result.data.created_at)}</p>
          <OrderView order={result.data} />
        </>
      )}
    </Container>
  );
}
