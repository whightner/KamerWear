import type { Metadata } from "next";
import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { Container } from "@/components/storefront/Container";
import { getCurrentUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Contact — KamerWear" };

export default async function ContactPage() {
  const user = await getCurrentUser();
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Help" }, { label: "Contact" }]} />
      <div className="mt-4 max-w-2xl">
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">Contact KamerWear</h1>
        <p className="mt-2 text-sm text-ink">
          Questions about sizing, delivery, an order or a return? Send us a message from your
          account; our team replies in the same conversation.
        </p>
        <div className="mt-6 rounded-xl border border-line bg-white p-5">
          {user ? (
            <>
              <Link
                href="/support/new"
                className="inline-flex h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
              >
                <MessageCircle className="size-4" aria-hidden="true" />
                Open a support conversation
              </Link>
              <p className="mt-3 text-sm text-muted">
                About a specific order? Use “Contact support” on the order page so we see it
                straight away. <Link href="/support" className="font-semibold text-ink underline underline-offset-2">Your conversations</Link>
              </p>
            </>
          ) : (
            <>
              <p className="text-sm text-ink">Log in to open a support conversation.</p>
              <div className="mt-3 flex flex-wrap gap-3">
                <Link href="/login?next=/support/new" className="inline-flex h-11 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black">
                  Log in
                </Link>
                <Link href="/register?next=/support/new" className="inline-flex h-11 items-center rounded-lg border border-ink px-5 text-sm font-semibold text-ink">
                  Create an account
                </Link>
              </div>
            </>
          )}
        </div>
        <p className="mt-4 text-xs text-muted">
          Support is online chat only in this demo: there is no phone line or support email yet.
        </p>
      </div>
    </Container>
  );
}
