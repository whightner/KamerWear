import type { Metadata } from "next";
import Link from "next/link";
import { Heart, MapPin, Package, Ruler, UserRound, type LucideIcon } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { Container } from "@/components/storefront/Container";
import { requireUser } from "@/lib/auth/session";

export const metadata: Metadata = { title: "My account — KamerWear" };

interface Tile {
  title: string;
  description: string;
  icon: LucideIcon;
  href?: string;
  badge?: string;
}

export default async function AccountPage() {
  const user = await requireUser("/account");
  const { first_name, last_name, phone } = user.profile;

  const tiles: Tile[] = [
    {
      title: "Profile",
      description: "Your name, phone number and password.",
      icon: UserRound,
      href: "/account/profile",
    },
    {
      title: "Favorites",
      description: "Items you saved during this visit (kept on this device only).",
      icon: Heart,
      href: "/favorites",
    },
    {
      title: "Orders",
      description: "Order history and tracking will appear here.",
      icon: Package,
      badge: "Coming soon",
    },
    {
      title: "Fit Profile",
      description: "Your measurements for Smart Fit size recommendations.",
      icon: Ruler,
      badge: "Coming soon",
    },
    {
      title: "Addresses",
      description: "Delivery addresses across Cameroon.",
      icon: MapPin,
      badge: "Coming soon",
    },
  ];

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "My account" }]} />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">
        Hi, {first_name}
      </h1>
      <p className="mt-1 text-sm text-muted">Manage your KamerWear account.</p>

      <section
        aria-labelledby="account-details"
        className="mt-6 rounded-xl border border-line bg-white p-5"
      >
        <h2 id="account-details" className="text-sm font-bold text-ink">
          Account details
        </h2>
        <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted">Name</dt>
            <dd className="font-medium text-ink">
              {first_name} {last_name}
            </dd>
          </div>
          <div className="min-w-0">
            <dt className="text-muted">Email</dt>
            <dd className="break-words font-medium text-ink">{user.email}</dd>
          </div>
          <div>
            <dt className="text-muted">Phone</dt>
            <dd className="font-medium text-ink">{phone ?? "Not added"}</dd>
          </div>
        </dl>
      </section>

      <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map(({ title, description, icon: Icon, href, badge }) => {
          const body = (
            <>
              <span className="flex size-10 items-center justify-center rounded-full bg-cream">
                <Icon className="size-5 text-ink" aria-hidden="true" />
              </span>
              <span className="mt-3 flex items-center gap-2">
                <span className="font-bold text-ink">{title}</span>
                {badge && (
                  <span className="rounded-full bg-sand px-2 py-0.5 text-[11px] font-semibold text-muted">
                    {badge}
                  </span>
                )}
              </span>
              <span className="mt-1 block text-sm text-muted">{description}</span>
            </>
          );
          return (
            <li key={title}>
              {href ? (
                <Link
                  href={href}
                  className="block h-full rounded-xl border border-line bg-white p-5 hover:border-ink"
                >
                  {body}
                </Link>
              ) : (
                <div className="h-full rounded-xl border border-dashed border-line bg-white/60 p-5">
                  {body}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Container>
  );
}
