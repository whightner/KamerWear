"use client";

import { useState } from "react";
import Form from "next/form";
import Link from "next/link";
import {
  Camera,
  Flame,
  Heart,
  Menu,
  Package,
  Search,
  ShoppingBag,
  User,
  X,
  type LucideIcon,
} from "lucide-react";
import { useStore } from "@/components/store/StoreProvider";
import { mainNavigation } from "@/data/navigation";
import { Container } from "./Container";
import { DeliveryCityButton } from "./DeliveryCityButton";
import { Logo } from "./Logo";

interface AccountLink {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Pages that don't exist yet are not prefetched. */
  prefetch?: false;
  count?: number;
}

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const { cartCount, favorites } = useStore();

  const accountLinks: AccountLink[] = [
    // Future route: order tracking arrives in a later task.
    {
      label: "Track order",
      href: "/orders/track",
      icon: Package,
      prefetch: false,
    },
    // Future route: accounts arrive in a later task.
    { label: "Account", href: "/account", icon: User, prefetch: false },
    {
      label: "Favorites",
      href: "/favorites",
      icon: Heart,
      count: favorites.size,
    },
    { label: "Cart", href: "/cart", icon: ShoppingBag, count: cartCount },
  ];

  return (
    <>
      <p className="bg-ink py-2 text-center text-[11px] font-semibold tracking-[0.2em] text-white">
        CAMEROON-WIDE DELIVERY • EASY RETURNS • SECURE CHECKOUT
      </p>

      <header className="sticky top-0 z-40 border-b border-line bg-white">
        <Container className="flex h-[72px] items-center gap-3 md:gap-6">
          <button
            type="button"
            className="-ml-2 rounded-md p-2 md:hidden"
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            aria-controls="main-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X className="size-5" /> : <Menu className="size-5" />}
          </button>

          <Logo />

          {/* GET form: submitting navigates to /shop?q=… (works without JavaScript too). */}
          <Form
            action="/shop"
            role="search"
            className="hidden h-11 min-w-0 max-w-2xl flex-1 items-center rounded-lg border border-line bg-cream/60 pl-3 focus-within:border-ink md:flex"
          >
            <Search className="size-4 shrink-0 text-muted" aria-hidden="true" />
            <label htmlFor="site-search" className="sr-only">
              Search products
            </label>
            <input
              id="site-search"
              name="q"
              type="search"
              placeholder="Search clothes, shoes, brands..."
              className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-muted"
            />
            <Link
              href="/#visual-search"
              aria-label="Search by image"
              title="Search by image"
              className="mr-1 flex h-9 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium text-ink hover:bg-sand"
            >
              <Camera className="size-[18px]" aria-hidden="true" />
              <span className="hidden lg:inline">Image</span>
            </Link>
            <button
              type="submit"
              className="h-full rounded-r-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
            >
              Search
            </button>
          </Form>

          <nav
            aria-label="Account"
            className="ml-auto flex items-center sm:gap-1"
          >
            {accountLinks.map(
              ({ label, href, icon: Icon, prefetch, count }) => (
                <Link
                  key={label}
                  href={href}
                  prefetch={prefetch}
                  aria-label={count ? `${label}, ${count} items` : label}
                  className="relative flex flex-col items-center gap-0.5 rounded-md px-2 py-1.5 text-[11px] font-medium text-ink hover:bg-cream sm:px-3"
                >
                  <Icon className="size-5" aria-hidden="true" />
                  <span aria-hidden="true" className="hidden lg:inline">
                    {label}
                  </span>
                  {count ? (
                    <span
                      aria-hidden="true"
                      className="absolute right-0.5 top-0 flex h-4 min-w-4 items-center justify-center rounded-full bg-deal px-1 text-[10px] font-bold text-white sm:right-1.5"
                    >
                      {count}
                    </span>
                  ) : null}
                </Link>
              ),
            )}
          </nav>
        </Container>

        <div className="border-t border-line">
          <Container className="flex items-center justify-between">
            <nav
              id="main-navigation"
              aria-label="Main"
              className={`${menuOpen ? "flex" : "hidden"} w-full flex-col py-2 md:flex md:w-auto md:flex-row md:py-0`}
            >
              {mainNavigation.map((link) => (
                <Link
                  key={link.label}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={`flex items-center gap-1.5 py-2.5 text-sm font-semibold md:mr-8 md:py-3 ${
                    link.highlight
                      ? "text-deal hover:text-deal-dark"
                      : "text-ink hover:text-muted"
                  }`}
                >
                  {link.highlight && (
                    <Flame className="size-4" aria-hidden="true" />
                  )}
                  {link.label}
                </Link>
              ))}
            </nav>
            <DeliveryCityButton className="hidden lg:flex" />
          </Container>
        </div>
      </header>
    </>
  );
}
