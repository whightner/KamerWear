import Link from "next/link";
import { ConversationStatusBadge } from "@/components/returns/ReturnBadges";
import { formatDateTime } from "@/lib/commerce/labels";
import type { AdminConversationSummary, ConversationSummary } from "@/lib/after-sales/types";

/** Conversations, latest activity first. `basePath` is /support or /admin/support. */
export function ConversationList({
  items,
  basePath,
}: {
  items: (ConversationSummary | AdminConversationSummary)[];
  basePath: string;
}) {
  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const customer = "customer" in item ? item.customer : null;
        return (
          <li key={item.conversation_number}>
            <Link
              href={`${basePath}/${item.conversation_number}`}
              className="block rounded-xl border border-line bg-white p-4 hover:border-ink"
            >
              <span className="flex flex-wrap items-center gap-2">
                <span className="font-bold text-ink">{item.subject_label}</span>
                <ConversationStatusBadge status={item.status} />
                {item.unread_count > 0 && (
                  <span className="rounded-full bg-deal px-2 py-0.5 text-xs font-bold text-white">
                    {item.unread_count} new
                  </span>
                )}
                <span className="ml-auto text-xs text-muted">
                  <span className="sr-only">Last activity </span>
                  {formatDateTime(item.last_message_at)}
                </span>
              </span>
              <span className="mt-1 block text-xs text-muted">
                {item.conversation_number}
                {customer && ` · ${customer.name} (${customer.email})`}
                {item.order_number && ` · Order ${item.order_number}`}
                {item.return_number && ` · Return ${item.return_number}`}
              </span>
              {item.last_message_preview && (
                <span className="mt-1 block truncate text-sm text-ink">
                  {item.last_message_role === "store" ? "KamerWear support: " : ""}
                  {item.last_message_preview}
                </span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
