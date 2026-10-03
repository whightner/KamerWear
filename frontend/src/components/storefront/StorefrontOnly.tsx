"use client";

import type { ReactNode } from "react";
import { usePathname } from "next/navigation";

/** Renders storefront chrome (header, footer, notices) everywhere except /admin,
 * which has its own layout. */
export function StorefrontOnly({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/admin" || pathname.startsWith("/admin/")) return null;
  return children;
}
