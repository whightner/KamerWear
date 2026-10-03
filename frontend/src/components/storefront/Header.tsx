"use client";

import { useState } from "react";
import {
  Camera,
  Flame,
  Heart,
  MapPin,
  Menu,
  Search,
  ShoppingBag,
  User,
  X,
} from "lucide-react";
import { mainNavigation } from "@/data/navigation";
import { Container } from "./Container";
import { Logo } from "./Logo";

const accountLinks = [
  { label: "Account", icon: User },
  { label: "Favorites", icon: Heart },
  { label: "Cart", icon: ShoppingBag },
];

export function Header() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <>
      <p
        id="top"
        className="bg-ink py-2 text-center text-[11px] font-semibold tracking-[0.2em] text-white"
      >
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

          {/* Search runs nothing yet: typing works, results arrive with the catalog API. */}
          <form
            role="search"
            onSubmit={(event) => event.preventDefault()}
            className="hidden h-11 min-w-0 max-w-2xl flex-1 items-center rounded-lg border border-line bg-cream/60 pl-3 focus-within:border-ink md:flex"
          >
            <Search className="size-4 shrink-0 text-muted" aria-hidden="true" />
            <label htmlFor="site-search" className="sr-only">
              Search products
            </label>
            <input
              id="site-search"
              type="search"
              placeholder="Search clothes, shoes, brands..."
              className="h-full min-w-0 flex-1 bg-transparent px-3 text-sm outline-none placeholder:text-muted"
            />
            <a
              href="#visual-search"
              aria-label="Search by image"
              title="Search by image"
              className="mr-1 flex h-9 items-center gap-1.5 rounded-md px-2.5 text-sm font-medium text-ink hover:bg-sand"
            >
              <Camera className="size-[18px]" aria-hidden="true" />
              <span className="hidden lg:inline">Image</span>
            </a>
            <button
              type="submit"
              className="h-full rounded-r-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
            >
              Search
            </button>
          </form>

          <nav
            aria-label="Account"
            className="ml-auto flex items-center sm:gap-1"
          >
            {accountLinks.map(({ label, icon: Icon }) => (
              <a
                key={label}
                href="#"
                aria-label={label}
                className="flex flex-col items-center gap-0.5 rounded-md px-2 py-1.5 text-[11px] font-medium text-ink hover:bg-cream sm:px-3"
              >
                <Icon className="size-5" aria-hidden="true" />
                <span aria-hidden="true" className="hidden lg:inline">
                  {label}
                </span>
              </a>
            ))}
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
                <a
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
                </a>
              ))}
            </nav>
            <p className="hidden items-center gap-1.5 text-xs text-muted lg:flex">
              <MapPin className="size-3.5" aria-hidden="true" />
              Delivering to{" "}
              <span className="font-semibold text-ink">Douala</span>
            </p>
          </Container>
        </div>
      </header>
    </>
  );
}
