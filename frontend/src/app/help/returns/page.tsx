import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { Container } from "@/components/storefront/Container";

export const metadata: Metadata = {
  title: "Returns — KamerWear",
  description: "How returns work at KamerWear (demo store).",
};

// The rules below describe exactly what the system enforces
// (backend/app/services/returns.py); nothing more is promised.
export default function ReturnsHelpPage() {
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Help" }, { label: "Returns" }]} />
      <article className="mt-4 max-w-3xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">Returns</h1>
        <p className="mt-2 rounded-lg bg-gold-soft px-4 py-2 text-sm text-ink">
          KamerWear is a demo store: these are the rules of the demo, and refunds are recorded
          manually without any real payment.
        </p>
        <div className="mt-6 space-y-6 text-sm leading-relaxed text-ink">
          <section>
            <h2 className="text-lg font-bold">Who can return what</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>Only items from an order that has been <strong>delivered</strong>.</li>
              <li>
                Within <strong>7 days</strong> of the delivery date shown on your order (not the
                order date).
              </li>
              <li>
                Up to the quantity you bought, minus what is already in another return request.
              </li>
            </ul>
          </section>
          <section>
            <h2 className="text-lg font-bold">How to request a return</h2>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li>Open the order in <Link href="/orders" className="font-semibold underline underline-offset-2">My orders</Link> and choose “Request a return”.</li>
              <li>Pick the items and quantities, a reason for each, and add details if useful.</li>
              <li>Review and submit. You get a return reference such as KR-2026-8M4PQ2.</li>
            </ol>
            <p className="mt-2">You can cancel a request yourself as long as our team hasn&apos;t reviewed it yet.</p>
          </section>
          <section>
            <h2 className="text-lg font-bold">What happens next</h2>
            <ol className="mt-2 list-decimal space-y-1 pl-5">
              <li><strong>Requested</strong>: our team reviews it and approves or rejects it, with a note.</li>
              <li><strong>Approved</strong>: send the items back as agreed with our team.</li>
              <li><strong>Received</strong>: we check the items. Items in good condition go back on sale; damaged items don&apos;t.</li>
              <li><strong>Refunded (demo)</strong>: the refund is recorded manually.</li>
            </ol>
          </section>
          <section>
            <h2 className="text-lg font-bold">Refunds</h2>
            <ul className="mt-2 list-disc space-y-1 pl-5">
              <li>The refund value is the price you paid for the returned items. Delivery fees are not refunded.</li>
              <li>In this demo no money moves: no Mobile Money, Orange Money or card refund is made. The return page says so when the refund is recorded.</li>
            </ul>
          </section>
          <section>
            <h2 className="text-lg font-bold">Photos</h2>
            <p className="mt-2">Photo evidence is planned for a later version with proper storage. For now, describe the issue in the details.</p>
          </section>
          <p>
            Questions? <Link href="/help/contact" className="font-semibold underline underline-offset-2">Contact support</Link>.
          </p>
        </div>
      </article>
    </Container>
  );
}
