import Link from "next/link";
import { Container } from "@/components/storefront/Container";

export default function NotFound() {
  return (
    <Container className="py-24 text-center">
      <p className="text-sm font-bold uppercase tracking-[0.2em] text-deal">
        404
      </p>
      <h1 className="mt-3 text-3xl font-extrabold tracking-tight text-ink">
        We couldn&apos;t find that page
      </h1>
      <p className="mx-auto mt-3 max-w-md text-muted">
        The page may have moved, or it is part of KamerWear that isn&apos;t
        built yet.
      </p>
      <div className="mt-8 flex justify-center gap-3">
        <Link
          href="/shop"
          className="inline-flex h-11 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
        >
          Browse the shop
        </Link>
        <Link
          href="/"
          className="inline-flex h-11 items-center rounded-lg border border-ink/80 px-5 text-sm font-semibold text-ink"
        >
          Go to homepage
        </Link>
      </div>
    </Container>
  );
}
