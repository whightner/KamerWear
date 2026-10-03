import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ConversationStatusBadge } from "@/components/returns/ReturnBadges";
import { Conversation } from "@/components/support/Conversation";
import { ConversationStatusForm } from "@/components/support/ConversationStatusForm";
import { Container } from "@/components/storefront/Container";
import { supportApi } from "@/lib/after-sales/api";
import { getAccessToken, requireUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "Support conversation — KamerWear" };

export default async function ConversationPage({ params }: PageProps<"/support/[number]">) {
  const { number } = await params;
  const ref = decodeURIComponent(number);
  await requireUser(`/support/${number}`);
  const result = await supportApi.detail((await getAccessToken()) ?? "", ref);
  // Another customer's conversation looks exactly like a missing one.
  if (!result.ok && result.status === 404) notFound();

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Support", href: "/support" }, { label: ref }]} />
      {!result.ok ? (
        <p role="alert" className="mt-6 rounded-xl border border-line bg-white px-6 py-10 text-center text-ink">
          We couldn&apos;t load this conversation right now. Please try again in a moment.
        </p>
      ) : (
        <div className="mt-4 max-w-3xl">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="text-2xl font-extrabold tracking-tight text-ink sm:text-3xl">
                  {result.data.subject_label}
                </h1>
                <ConversationStatusBadge status={result.data.status} />
              </div>
              <p className="mt-1 text-sm text-muted">
                {result.data.conversation_number}
                {result.data.order_number && (
                  <>
                    {" · "}
                    <Link href={`/orders/${result.data.order_number}`} className="font-semibold text-ink underline underline-offset-2">
                      Order {result.data.order_number}
                    </Link>
                  </>
                )}
                {result.data.return_number && (
                  <>
                    {" · "}
                    <Link href={`/returns/${result.data.return_number}`} className="font-semibold text-ink underline underline-offset-2">
                      Return {result.data.return_number}
                    </Link>
                  </>
                )}
              </p>
            </div>
            <ConversationStatusForm number={result.data.conversation_number} status={result.data.status} />
          </div>
          <div className="mt-5">
            <Conversation
              key={result.data.status}
              mode="customer"
              number={result.data.conversation_number}
              initialMessages={result.data.messages}
              initialLastId={result.data.last_message_id}
              status={result.data.status}
            />
          </div>
        </div>
      )}
    </Container>
  );
}
