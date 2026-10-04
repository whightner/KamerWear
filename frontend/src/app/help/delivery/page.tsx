import type { Metadata } from "next";
import Link from "next/link";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { Container } from "@/components/storefront/Container";
import { formatXaf } from "@/lib/format";

export const metadata: Metadata = {
  title: "Delivery — KamerWear",
  description: "How delivery works at KamerWear (demo store).",
};

// Mirrors backend/app/services/delivery.py (the API calculates the real fee).
const FEES = [
  ["Douala", 1500],
  ["Yaoundé", 2000],
  ["Bafoussam", 2500],
  ["Other cities in Cameroon", 3500],
] as const;

export default function DeliveryHelpPage() {
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Help" }, { label: "Delivery" }]} />
      <article className="mt-4 max-w-3xl text-sm leading-relaxed text-ink">
        <h1 className="text-3xl font-extrabold tracking-tight">Delivery</h1>
        <p className="mt-2 rounded-lg bg-gold-soft px-4 py-2">
          KamerWear is a demo store: no courier company is connected, and fees and timings are
          demo values.
        </p>
        <h2 className="mt-6 text-lg font-bold">Delivery fees</h2>
        <p className="mt-1">A flat fee per city, added at checkout and calculated by our server:</p>
        <table className="mt-3 w-full max-w-md text-left">
          <caption className="sr-only">Delivery fee per city</caption>
          <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
            <tr>
              <th scope="col" className="py-2">City</th>
              <th scope="col" className="py-2 text-right">Fee</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {FEES.map(([city, fee]) => (
              <tr key={city}>
                <td className="py-2">{city}</td>
                <td className="py-2 text-right font-semibold">{formatXaf(fee)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <h2 className="mt-6 text-lg font-bold">Following your order</h2>
        <p className="mt-1">
          Every order goes through: placed, confirmed, preparing, shipped, out for delivery and
          delivered. Our team updates the status, and you can follow it in{" "}
          <Link href="/orders" className="font-semibold underline underline-offset-2">My orders</Link> or
          with your order number on{" "}
          <Link href="/orders/track" className="font-semibold underline underline-offset-2">Track order</Link>.
        </p>
        <h2 className="mt-6 text-lg font-bold">Paying</h2>
        <p className="mt-1">
          Cash on delivery, or Mobile Money and card as demo options: no money is actually taken.
        </p>
        <p className="mt-6">
          Questions? <Link href="/help/contact" className="font-semibold underline underline-offset-2">Contact support</Link>.
          {" "}Returns are explained on the <Link href="/help/returns" className="font-semibold underline underline-offset-2">returns page</Link>.
        </p>
      </article>
    </Container>
  );
}
