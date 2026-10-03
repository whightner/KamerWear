"use client";

import { RefreshCw } from "lucide-react";
import { Container } from "@/components/storefront/Container";

// Last-resort boundary for unexpected errors in a page. Header and footer
// (root layout) stay visible. Catalog outages are normally handled inline.
export default function Error({ retry }: { error: Error; retry: () => void }) {
  return (
    <Container className="py-24 text-center">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">
        Something went wrong loading this page.
      </h1>
      <p className="mx-auto mt-2 max-w-md text-muted">
        Please try again in a moment.
      </p>
      <button
        type="button"
        onClick={() => retry()}
        className="mt-6 inline-flex h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white"
      >
        <RefreshCw className="size-4" aria-hidden="true" />
        Try again
      </button>
    </Container>
  );
}
