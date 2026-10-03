import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { AddressBook } from "@/components/commerce/AddressBook";
import { Container } from "@/components/storefront/Container";
import { getAccessToken, requireUser } from "@/lib/auth/session";
import { commerceApi } from "@/lib/commerce/api";

export const metadata: Metadata = { title: "Addresses — KamerWear" };

export default async function AddressesPage() {
  const user = await requireUser("/account/addresses");
  const result = await commerceApi.addresses((await getAccessToken()) ?? "");

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "My account", href: "/account" },
          { label: "Addresses" },
        ]}
      />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Delivery addresses</h1>
      <p className="mb-6 mt-1 text-sm text-muted">
        Where we deliver your orders. Landmarks help the courier find you.
      </p>
      {result.ok ? (
        <AddressBook
          addresses={result.data}
          defaults={{
            recipient_name: `${user.profile.first_name} ${user.profile.last_name}`,
            phone: user.profile.phone ?? "",
          }}
        />
      ) : (
        <p role="alert" className="rounded-xl border border-line bg-white px-6 py-10 text-center text-sm text-ink">
          We couldn&apos;t load your addresses right now. Please try again in a moment.
        </p>
      )}
    </Container>
  );
}
