import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { NewConversationForm } from "@/components/support/NewConversationForm";
import { Container } from "@/components/storefront/Container";
import { requireUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "New support conversation — KamerWear" };

function one(value: string | string[] | undefined) {
  const v = Array.isArray(value) ? value[0] : value;
  return v && /^[A-Za-z0-9-]{1,20}$/.test(v) ? v.toUpperCase() : undefined;
}

export default async function NewConversationPage({ searchParams }: PageProps<"/support/new">) {
  const sp = await searchParams;
  const order = one(sp.order);
  const ret = one(sp.return);
  await requireUser(`/support/new${order ? `?order=${order}` : ret ? `?return=${ret}` : ""}`);

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Support", href: "/support" }, { label: "New conversation" }]} />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">New conversation</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Our team replies here; the conversation updates by itself while it&apos;s open.
      </p>
      <div className="mt-6 max-w-2xl rounded-xl border border-line bg-white p-5">
        <NewConversationForm
          orderNumber={order}
          returnNumber={ret}
          defaultSubject={ret ? "return_question" : order ? "order_issue" : undefined}
        />
      </div>
    </Container>
  );
}
