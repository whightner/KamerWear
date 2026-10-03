"use client";

import { useEffect, useId, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, LayoutDashboard, LogOut, User, UserRound } from "lucide-react";
import { logoutAction } from "@/lib/auth/actions";

// Header menu for a signed-in customer: "Hi, Alex" with Account, Profile and
// Log out. Logging out is a form POST to a Server Action, so it works even
// before JavaScript has loaded.
export function AccountMenu({ firstName, isAdmin }: { firstName: string; isAdmin: boolean }) {
  const [open, setOpen] = useState(false);
  const menuId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const itemClass =
    "flex w-full items-center gap-2.5 rounded-md px-3 py-2 text-left text-sm font-medium text-ink hover:bg-cream";

  return (
    <div ref={rootRef} className="relative">
      <button
        ref={buttonRef}
        type="button"
        aria-expanded={open}
        aria-controls={menuId}
        aria-label={`Account menu for ${firstName}`}
        onClick={() => setOpen((value) => !value)}
        className="flex flex-col items-center gap-0.5 rounded-md px-2 py-1.5 text-[11px] font-medium text-ink hover:bg-cream sm:px-3"
      >
        <User className="size-5" aria-hidden="true" />
        <span aria-hidden="true" className="hidden max-w-24 items-center gap-0.5 lg:flex">
          <span className="truncate">Hi, {firstName}</span>
          <ChevronDown className="size-3 shrink-0" />
        </span>
      </button>

      {open && (
        <div
          id={menuId}
          className="absolute right-0 top-full z-50 mt-1 w-52 rounded-lg border border-line bg-white p-1.5 shadow-lg"
        >
          <p className="truncate px-3 pb-2 pt-1 text-xs text-muted">
            Signed in as {firstName}
          </p>
          <ul>
            <li>
              <Link href="/account" className={itemClass} onClick={() => setOpen(false)}>
                <User className="size-4" aria-hidden="true" />
                My account
              </Link>
            </li>
            <li>
              <Link href="/account/profile" className={itemClass} onClick={() => setOpen(false)}>
                <UserRound className="size-4" aria-hidden="true" />
                Profile
              </Link>
            </li>
            {isAdmin && (
              <li>
                <Link href="/admin" className={itemClass} onClick={() => setOpen(false)}>
                  <LayoutDashboard className="size-4" aria-hidden="true" />
                  Store admin
                </Link>
              </li>
            )}
            <li className="mt-1 border-t border-line pt-1">
              <form action={logoutAction}>
                <button type="submit" className={itemClass}>
                  <LogOut className="size-4" aria-hidden="true" />
                  Log out
                </button>
              </form>
            </li>
          </ul>
        </div>
      )}
    </div>
  );
}
