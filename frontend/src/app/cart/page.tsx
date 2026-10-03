import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { CartView } from "@/components/store/CartView";
import { Container } from "@/components/storefront/Container";

export const metadata: Metadata = { title: "Cart — KamerWear" };

export default function CartPage() {
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Cart" }]} />
      <h1 className="mb-6 mt-4 text-3xl font-extrabold tracking-tight text-ink">
        Your cart
      </h1>
      <CartView />
    </Container>
  );
}
