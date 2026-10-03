"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Boxes,
  ClipboardList,
  LayoutDashboard,
  MessageCircle,
  Package,
  RotateCcw,
  ScanSearch,
  Store,
  Tags,
  type LucideIcon,
} from "lucide-react";

type Badge = "returns" | "support";

const LINKS: { href: string; label: string; icon: LucideIcon; badge?: Badge }[] = [
  { href: "/admin", label: "Dashboard", icon: LayoutDashboard },
  { href: "/admin/products", label: "Products", icon: Package },
  { href: "/admin/categories", label: "Categories", icon: Tags },
  { href: "/admin/inventory", label: "Inventory", icon: Boxes },
  { href: "/admin/orders", label: "Orders", icon: ClipboardList },
  { href: "/admin/returns", label: "Returns", icon: RotateCcw, badge: "returns" },
  { href: "/admin/support", label: "Support", icon: MessageCircle, badge: "support" },
  { href: "/admin/visual-search", label: "Visual search", icon: ScanSearch },
];

/** Counts shown next to Returns (to process) and Support (unread conversations). */
export function AdminNav({ counts }: { counts?: Record<Badge, number> }) {
  const pathname = usePathname();
  const isCurrent = (href: string) =>
    href === "/admin" ? pathname === "/admin" : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <nav aria-label="Admin" className="relative flex gap-1 overflow-x-auto lg:flex-col">
      {LINKS.map(({ href, label, icon: Icon, badge }) => {
        const current = isCurrent(href);
        const count = badge ? (counts?.[badge] ?? 0) : 0;
        return (
          <Link
            key={href}
            href={href}
            aria-current={current ? "page" : undefined}
            className={`flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold ${
              current ? "bg-white text-ink shadow-sm" : "text-white/80 hover:bg-white/10 hover:text-white"
            }`}
          >
            <Icon className="size-4" aria-hidden="true" />
            {label}
            {count > 0 && (
              <span className="ml-auto rounded-full bg-gold px-1.5 text-xs font-bold text-ink">
                {count}
                <span className="sr-only">
                  {badge === "returns" ? " returns to process" : " conversations with unread messages"}
                </span>
              </span>
            )}
          </Link>
        );
      })}
      <Link
        href="/"
        className="flex shrink-0 items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-semibold text-white/80 hover:bg-white/10 hover:text-white lg:mt-4"
      >
        <Store className="size-4" aria-hidden="true" />
        Back to store
      </Link>
    </nav>
  );
}
