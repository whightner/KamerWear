import Link from "next/link";
import { notFound } from "next/navigation";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { StatusBadge } from "@/components/commerce/StatusBadge";
import { ConversationStatusBadge, ReturnStatusBadge } from "@/components/returns/ReturnBadges";
import { Conversation } from "@/components/support/Conversation";
import { ConversationStatusForm } from "@/components/support/ConversationStatusForm";
import { adminToken } from "@/lib/admin/page";
import { supportApi } from "@/lib/after-sales/api";
import { formatDateTime } from "@/lib/commerce/labels";
import { formatXaf } from "@/lib/format";

export default async function AdminConversationPage({ params }: PageProps<"/admin/support/[number]">) {
  const { number } = await params;
  const ref = decodeURIComponent(number);
  const token = await adminToken(`/admin/support/${number}`);
  if (!token) return null;
  const result = await supportApi.adminDetail(token, ref);
  if (!result.ok && result.status === 404) notFound();
  if (!result.ok) return <AdminError what="this conversation" />;
  const d = result.data;

  return (
    <>
      <AdminHeading
        title={d.subject_label}
        description={`${d.conversation_number} · started ${formatDateTime(d.created_at)}`}
        actions={
          <div className="flex items-center gap-3">
            <ConversationStatusBadge status={d.status} />
            <ConversationStatusForm number={d.conversation_number} status={d.status} admin />
          </div>
        }
      />
      <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
        <div className="min-w-0">
          <Conversation
            key={d.status}
            mode="admin"
            number={d.conversation_number}
            initialMessages={d.messages}
            initialLastId={d.last_message_id}
            status={d.status}
          />
        </div>
        <Panel title="Context">
          <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
            <dt className="text-muted">Customer</dt>
            <dd className="min-w-0 break-words text-ink">
              {d.customer.name}
              <br />
              <span className="text-xs text-muted">{d.customer.email}</span>
            </dd>
            {d.order && (
              <>
                <dt className="text-muted">Order</dt>
                <dd>
                  <Link href={`/admin/orders/${d.order.order_number}`} className="font-semibold text-ink underline underline-offset-2">
                    Order {d.order.order_number}
                  </Link>
                  <span className="mt-1 flex items-center gap-2 text-xs text-muted">
                    <StatusBadge status={d.order.status} /> {formatXaf(d.order.total)}
                  </span>
                </dd>
              </>
            )}
            {d.return_request && (
              <>
                <dt className="text-muted">Return</dt>
                <dd>
                  <Link href={`/admin/returns/${d.return_request.return_number}`} className="font-semibold text-ink underline underline-offset-2">
                    Return {d.return_request.return_number}
                  </Link>
                  <span className="mt-1 flex items-center gap-2 text-xs text-muted">
                    <ReturnStatusBadge status={d.return_request.status} /> {formatXaf(d.return_request.return_value)}
                  </span>
                </dd>
              </>
            )}
            {!d.order && !d.return_request && (
              <>
                <dt className="text-muted">Linked to</dt>
                <dd className="text-ink">General question</dd>
              </>
            )}
          </dl>
        </Panel>
      </div>
    </>
  );
}
