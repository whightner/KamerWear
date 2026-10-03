import type { ReactNode } from "react";
import Link from "next/link";
import { LogOut } from "lucide-react";
import { logoutAction } from "@/lib/auth/actions";
import type { User } from "@/lib/auth/api";
import { AdminNav } from "./AdminNav";

/** Operational layout: dark sidebar, cream workspace. */
export function AdminShell({
  user,
  counts,
  children,
}: {
  user: User;
  counts?: { returns: number; support: number };
  children: ReactNode;
}) {
  return (
    <div className="min-h-screen bg-cream lg:grid lg:grid-cols-[232px_1fr]">
      <aside className="relative bg-ink px-4 py-4 text-white lg:sticky lg:top-0 lg:h-screen lg:py-6">
        <div className="mb-4 flex items-center justify-between gap-3 lg:mb-8 lg:block">
          <Link href="/admin" className="text-lg font-black tracking-tight">
            KAMER<span className="text-gold">WEAR</span>
            <span className="ml-2 rounded bg-white/15 px-1.5 py-0.5 align-middle text-[10px] font-bold tracking-wider">
              ADMIN
            </span>
          </Link>
        </div>
        <AdminNav counts={counts} />
        <div className="mt-4 border-t border-white/15 pt-4 text-sm lg:absolute lg:inset-x-4 lg:bottom-6">
          <p className="truncate font-semibold">
            {user.profile.first_name} {user.profile.last_name}
          </p>
          <p className="truncate text-xs text-white/70">{user.email}</p>
          <div className="mt-2 flex gap-3 text-xs">
            <Link href="/account/profile" className="font-semibold text-white/85 underline-offset-2 hover:underline">
              Admin account
            </Link>
            <form action={logoutAction}>
              <button type="submit" className="flex items-center gap-1 font-semibold text-white/85 hover:underline">
                <LogOut className="size-3.5" aria-hidden="true" />
                Log out
              </button>
            </form>
          </div>
        </div>
      </aside>
      <div className="min-w-0 px-4 py-6 sm:px-6 lg:px-8">{children}</div>
    </div>
  );
}

export function AdminHeading({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      {actions}
    </div>
  );
}

export function Panel({
  title,
  children,
  className = "",
  actions,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
  actions?: ReactNode;
}) {
  return (
    <section
      aria-label={title}
      className={`min-w-0 rounded-xl border border-line bg-white p-4 sm:p-5 ${className}`}
    >
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          {title && <h2 className="text-base font-bold text-ink">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}
