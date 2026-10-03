import {
  Headphones,
  RotateCcw,
  ShieldCheck,
  Truck,
  type LucideIcon,
} from "lucide-react";
import { Container } from "./Container";

// Demo wording: final delivery areas, payment methods and policies are not set yet.
const promises: { title: string; text: string; icon: LucideIcon }[] = [
  {
    title: "Delivery in Cameroon",
    text: "Delivery to supported cities such as Douala and Yaoundé. Fees and timing shown at checkout.",
    icon: Truck,
  },
  {
    title: "Secure checkout",
    text: "Encrypted payment flow, with Mobile Money and card options planned.",
    icon: ShieldCheck,
  },
  {
    title: "Customer support",
    text: "Questions about sizing or an order? Our team is here to help.",
    icon: Headphones,
  },
  {
    title: "Easy returns",
    text: "Return eligible items under our returns policy. Details on each product page.",
    icon: RotateCcw,
  },
];

export function TrustSection() {
  return (
    <section
      id="delivery"
      aria-labelledby="delivery-title"
      className="pb-16 pt-14"
    >
      <Container>
        <h2 id="delivery-title" className="sr-only">
          Delivery and shopping with KamerWear
        </h2>
        <ul className="grid gap-4 rounded-2xl border border-line bg-white p-6 sm:grid-cols-2 lg:grid-cols-4 lg:p-8">
          {promises.map(({ title, text, icon: Icon }) => (
            <li key={title} className="flex gap-4">
              <span className="flex size-11 shrink-0 items-center justify-center rounded-full bg-cream text-ink">
                <Icon className="size-5" aria-hidden="true" />
              </span>
              <span>
                <span className="block text-sm font-bold text-ink">
                  {title}
                </span>
                <span className="mt-1 block text-sm leading-snug text-muted">
                  {text}
                </span>
              </span>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
