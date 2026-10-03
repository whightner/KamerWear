import type { Metadata } from "next";
import Link from "next/link";
import { MessageCircle, Plus } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ConversationList } from "@/components/support/ConversationList";
import { Container } from "@/components/storefront/Container";
import { supportApi } from "@/lib/after-sales/api";
import { getAccessToken, requireUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Support — KamerWear" };

export default async function SupportPage() {
  await requireUser("/support");
  const result = await supportApi.list((await getAccessToken()) ?? "", { limit: 50 });

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "My account", href: "/account" }, { label: "Support" }]} />
      <div className="mt-4 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Support</h1>
          <p className="mt-1 text-sm text-muted">Your conversations with the KamerWear team.</p>
        </div>
        <Link
          href="/support/new"
          className="inline-flex h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
        >
          <Plus className="size-4" aria-hidden="true" />
          New conversation
        </Link>
      </div>
      <div className="mt-6 max-w-4xl">
        {!result.ok ? (
          <p role="alert" className="rounded-xl border border-line bg-white px-6 py-10 text-center text-ink">
            We couldn&apos;t load your conversations right now. Please try again in a moment.
          </p>
        ) : result.data.items.length === 0 ? (
          <div className="rounded-xl border border-line bg-white px-6 py-12 text-center">
            <MessageCircle className="mx-auto size-8 text-muted" aria-hidden="true" />
            <p className="mt-2 font-semibold text-ink">No conversations yet</p>
            <p className="mt-1 text-sm text-muted">
              Questions about sizing, delivery, an order or a return? Start a conversation.
            </p>
          </div>
        ) : (
          <ConversationList items={result.data.items} basePath="/support" />
        )}
      </div>
    </Container>
  );
}
