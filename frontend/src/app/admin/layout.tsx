import type { Metadata } from "next";
import Link from "next/link";
import { ShieldAlert } from "lucide-react";
import { AdminShell } from "@/components/admin/AdminShell";
import { returnsApi } from "@/lib/after-sales/api";
import { getAccessToken, requireAdmin } from "@/lib/auth/session";

export const metadata: Metadata = {
  title: "Admin — KamerWear",
  robots: { index: false, follow: false },
};

// Server-side gate for every /admin page: signed-out visitors are redirected
// to /login, customers see "not authorized" and no admin content is rendered.
// The API enforces the same rule on every admin endpoint.
export default async function AdminLayout({ children }: LayoutProps<"/admin">) {
  const admin = await requireAdmin("/admin");
  if (!admin) {
    return (
      <div className="flex min-h-[70vh] items-center justify-center bg-cream px-4">
        <div role="alert" className="max-w-md rounded-2xl border border-line bg-white p-8 text-center">
          <ShieldAlert className="mx-auto size-10 text-deal-dark" aria-hidden="true" />
          <h1 className="mt-3 text-2xl font-extrabold text-ink">Not authorized</h1>
          <p className="mt-2 text-sm text-muted">
            The store admin is only for KamerWear staff. Your account is a customer account.
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Link href="/" className="inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white">
              Back to the store
            </Link>
            <Link href="/account" className="inline-flex h-10 items-center rounded-lg border border-line px-5 text-sm font-semibold text-ink">
              My account
            </Link>
          </div>
        </div>
      </div>
    );
  }
  const attention = await returnsApi.attention((await getAccessToken()) ?? "");
  const counts = attention.ok
    ? { returns: attention.data.returns_to_process, support: attention.data.conversations_unread }
    : undefined;
  return (
    <AdminShell user={admin} counts={counts}>
      {children}
    </AdminShell>
  );
}
