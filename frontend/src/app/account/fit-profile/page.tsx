import type { Metadata } from "next";
import Link from "next/link";
import { Ruler, ScanLine } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { FormMessage } from "@/components/auth/fields";
import { ConfidenceBadge, MeasurementList } from "@/components/fit/FitDisplay";
import {
  DeleteFitProfile,
  EditFitProfile,
  FitProfileForm,
} from "@/components/fit/FitProfileManager";
import { Container } from "@/components/storefront/Container";
import { requireUser } from "@/lib/auth/session";
import { getFitProfile } from "@/lib/fit/api";
import { PREFERENCES, SOURCE_TEXT } from "@/lib/fit/types";

export const metadata: Metadata = { title: "Fit Profile — KamerWear" };

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "long",
    timeStyle: "short",
    timeZone: "Africa/Douala",
  }).format(new Date(value));
}

export default async function FitProfilePage({
  searchParams,
}: PageProps<"/account/fit-profile">) {
  await requireUser("/account/fit-profile");
  const { saved, deleted } = await searchParams;
  const profile = await getFitProfile();

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "My account", href: "/account" },
          { label: "Fit Profile" },
        ]}
      />
      <h1 className="mt-4 flex items-center gap-2 text-3xl font-extrabold tracking-tight text-ink">
        <Ruler className="size-7 text-fit" aria-hidden="true" />
        Fit Profile
      </h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        The sizes you confirmed. KamerWear uses them to recommend a size on Smart Fit products; it
        never selects a size or changes your cart for you.
      </p>

      <div className="mt-4 max-w-3xl">
        <FormMessage
          success={
            saved
              ? "Your Fit Profile is saved."
              : deleted
                ? "Your Fit Profile was deleted."
                : undefined
          }
        />
      </div>

      {profile === "unavailable" ? (
        <p role="alert" className="mt-6 max-w-3xl rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm text-deal-dark">
          We couldn&apos;t load your Fit Profile right now. Please try again in a moment.
        </p>
      ) : profile === null ? (
        <section aria-labelledby="no-profile" className="mt-6 max-w-3xl space-y-6">
          <div className="rounded-2xl bg-fit-soft p-6">
            <h2 id="no-profile" className="text-lg font-bold text-ink">
              You don&apos;t have a Fit Profile yet
            </h2>
            <p className="mt-1 text-sm text-ink">
              Take two guided photos to get suggested sizes, or enter the sizes you usually wear.
            </p>
            <Link
              href="/fit"
              className="mt-4 inline-flex h-11 items-center gap-2 rounded-lg bg-fit px-5 text-sm font-semibold text-white hover:bg-fit-dark"
            >
              <ScanLine className="size-4" aria-hidden="true" />
              Create My Fit Profile
            </Link>
          </div>
          <div className="rounded-2xl border border-line bg-white p-6">
            <h2 className="text-lg font-bold text-ink">Or enter your sizes yourself</h2>
            <div className="mt-4">
              <FitProfileForm profile={null} />
            </div>
          </div>
        </section>
      ) : (
        <div className="mt-6 max-w-3xl space-y-6">
          <section aria-labelledby="your-sizes" className="rounded-2xl border border-line bg-white p-6">
            <h2 id="your-sizes" className="text-lg font-bold text-ink">
              Your confirmed sizes
            </h2>
            <dl className="mt-4 grid grid-cols-3 gap-3">
              <div className="rounded-xl bg-cream p-3">
                <dt className="text-xs text-muted">Tops</dt>
                <dd className="text-2xl font-extrabold text-ink">{profile.top_size ?? "—"}</dd>
              </div>
              <div className="rounded-xl bg-cream p-3">
                <dt className="text-xs text-muted">Trousers</dt>
                <dd className="text-2xl font-extrabold text-ink">
                  {profile.bottom_size ?? "—"}
                  {profile.bottom_size_letter && (
                    <span className="ml-1 text-sm font-semibold text-muted">
                      ({profile.bottom_size_letter})
                    </span>
                  )}
                </dd>
              </div>
              <div className="rounded-xl bg-cream p-3">
                <dt className="text-xs text-muted">Confirmed shoe size</dt>
                <dd className="text-2xl font-extrabold text-ink">
                  {profile.shoe_size_eu ? `EU ${profile.shoe_size_eu}` : "—"}
                </dd>
              </div>
            </dl>
            <dl className="mt-5 grid gap-x-8 gap-y-2 text-sm sm:grid-cols-[auto_1fr]">
              <dt className="text-muted">Height</dt>
              <dd className="text-ink">{profile.height_cm} cm</dd>
              <dt className="text-muted">Fit preference</dt>
              <dd className="text-ink">
                {PREFERENCES.find((p) => p.value === profile.fit_preference)?.label}
              </dd>
              <dt className="text-muted">Source</dt>
              <dd className="text-ink">{SOURCE_TEXT[profile.source]}</dd>
              {profile.confidence && (
                <>
                  <dt className="text-muted">Photo estimate</dt>
                  <dd>
                    <ConfidenceBadge confidence={profile.confidence} />
                  </dd>
                </>
              )}
              <dt className="text-muted">Last updated</dt>
              <dd className="text-ink">{formatDate(profile.updated_at)}</dd>
            </dl>
            {profile.source !== "manual" && (
              <div className="mt-5 border-t border-line pt-4">
                <h3 className="text-sm font-bold text-ink">Estimated body dimensions</h3>
                <p className="mt-1 text-xs text-muted">
                  Approximate values from your photos, kept to explain the suggestion. Not
                  tailor measurements.
                </p>
                <MeasurementList measurements={profile.estimated_measurements} />
              </div>
            )}
          </section>

          <section aria-label="Fit Profile actions" className="flex flex-wrap items-start gap-3">
            <EditFitProfile profile={profile} />
            <Link
              href="/fit"
              className="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-fit px-4 text-sm font-semibold text-white hover:bg-fit-dark"
            >
              <ScanLine className="size-4" aria-hidden="true" />
              Rescan with new photos
            </Link>
            <DeleteFitProfile />
          </section>
        </div>
      )}
    </Container>
  );
}
