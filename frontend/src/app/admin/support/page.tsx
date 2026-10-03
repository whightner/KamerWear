import Form from "next/form";
import { AdminError } from "@/components/admin/AdminError";
import { AdminHeading, Panel } from "@/components/admin/AdminShell";
import { Pagination } from "@/components/admin/Pagination";
import { ConversationList } from "@/components/support/ConversationList";
import { adminToken, param } from "@/lib/admin/page";
import { supportApi } from "@/lib/after-sales/api";

const LIMIT = 25;

export default async function AdminSupportPage({ searchParams }: PageProps<"/admin/support">) {
  const token = await adminToken("/admin/support");
  if (!token) return null;
  const sp = await searchParams;
  const filters = {
    q: param(sp.q),
    status: param(sp.status),
    unread_only: param(sp.unread_only) === "true" ? "true" : undefined,
  };
  const offset = Number(param(sp.offset)) || 0;
  const result = await supportApi.adminList(token, { ...filters, limit: LIMIT, offset });
  const control = "h-10 w-full rounded-lg border border-line bg-white px-3 text-sm";
  const label = "mb-1 block text-xs font-semibold text-ink";

  return (
    <>
      <AdminHeading title="Support" description="Customer conversations, latest activity first." />
      <Panel>
        <Form action="/admin/support" role="search" aria-label="Filter conversations" className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_150px_auto_auto] lg:items-end">
          <div>
            <label htmlFor="support-q" className={label}>Search</label>
            <input id="support-q" name="q" defaultValue={filters.q} placeholder="Customer, email, order, return or conversation number" className={control} />
          </div>
          <div>
            <label htmlFor="support-status" className={label}>Status</label>
            <select id="support-status" name="status" defaultValue={filters.status ?? ""} className={control}>
              <option value="">Open and closed</option>
              <option value="open">Open</option>
              <option value="closed">Closed</option>
            </select>
          </div>
          <label className="flex h-10 items-center gap-2 text-sm text-ink">
            <input type="checkbox" name="unread_only" value="true" defaultChecked={!!filters.unread_only} />
            Unread only
          </label>
          <button type="submit" className="h-10 rounded-lg bg-ink px-4 text-sm font-semibold text-white hover:bg-black">Apply</button>
        </Form>
        {!result.ok ? (
          <AdminError what="conversations" />
        ) : result.data.items.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">No conversations match.</p>
        ) : (
          <>
            <ConversationList items={result.data.items} basePath="/admin/support" />
            <Pagination basePath="/admin/support" params={filters} total={result.data.total} limit={LIMIT} offset={offset} />
          </>
        )}
      </Panel>
    </>
  );
}
