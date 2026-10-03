import type { Metadata } from "next";
import Link from "next/link";
import { Ruler } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { FitFlow } from "@/components/fit/FitFlow";
import { FitPrivacy } from "@/components/fit/FitPrivacy";
import { Container } from "@/components/storefront/Container";
import { getCurrentUser } from "@/lib/auth/session";
import { getFitProfile } from "@/lib/fit/api";

export const metadata: Metadata = {
  title: "Smart Fit — KamerWear",
  description:
    "Create your Fit Profile: enter your height, take two guided photos, review the estimated sizes and confirm.",
};

const HOW = [
  "Enter your height (it sets the scale).",
  "Take a front photo and, for a better estimate, a side photo.",
  "A pretrained pose model finds your body outline; KamerWear estimates approximate dimensions and suggests sizes from its size charts.",
  "You review, correct anything and confirm. Only then is your Fit Profile saved.",
];

export default async function FitPage() {
  const user = await getCurrentUser();
  const profile = user ? await getFitProfile() : null;

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Smart Fit" }]} />
      <h1 className="mt-4 flex items-center gap-2 text-3xl font-extrabold tracking-tight text-ink">
        <Ruler className="size-7 text-fit" aria-hidden="true" />
        Create your Fit Profile
      </h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Smart Fit suggests clothing sizes from your height and two photos. It gives estimates to
        help you choose, not exact measurements, and you always confirm the result.
      </p>

      {user ? (
        <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <div className="min-w-0">
            {profile === "unavailable" && (
              <p role="status" className="mb-4 rounded-lg bg-sand px-4 py-3 text-sm text-ink">
                We couldn&apos;t load your saved Fit Profile, but you can still create a new one.
              </p>
            )}
            <FitFlow profile={profile === "unavailable" ? null : profile} />
          </div>
          <FitPrivacy />
        </div>
      ) : (
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <section aria-labelledby="fit-how" className="rounded-2xl bg-fit-soft p-6">
            <h2 id="fit-how" className="text-lg font-bold text-ink">
              How Smart Fit works
            </h2>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-ink">
              {HOW.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
            <p className="mt-4 text-sm text-ink">
              Log in or create an account to start: your Fit Profile is saved to your account.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href="/login?next=/fit"
                className="inline-flex h-11 items-center rounded-lg bg-fit px-5 text-sm font-semibold text-white hover:bg-fit-dark"
              >
                Log in to start
              </Link>
              <Link
                href="/register?next=/fit"
                className="inline-flex h-11 items-center rounded-lg border border-ink px-5 text-sm font-semibold text-ink hover:bg-white"
              >
                Create an account
              </Link>
            </div>
          </section>
          <FitPrivacy />
        </div>
      )}
    </Container>
  );
}
