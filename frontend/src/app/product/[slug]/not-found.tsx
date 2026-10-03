import Link from "next/link";
import { Container } from "@/components/storefront/Container";

export default function ProductNotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-deal">
        Product not found
      </p>
      <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink">
        This product isn&apos;t available
      </h1>
      <p className="mx-auto mt-3 max-w-md text-muted">
        The link may be out of date, or the product was removed from the demo
        catalog.
      </p>
      <Link
        href="/shop"
        className="mt-8 inline-flex h-11 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
      >
        Browse all products
      </Link>
    </Container>
  );
}
