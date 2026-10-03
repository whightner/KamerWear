import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { FavoritesView } from "@/components/store/FavoritesView";
import { Container } from "@/components/storefront/Container";

export const metadata: Metadata = { title: "Favorites — KamerWear" };

export default function FavoritesPage() {
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[{ label: "Home", href: "/" }, { label: "Favorites" }]}
      />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">
        Favorites
      </h1>
      <p className="mb-6 mt-1 text-sm text-muted">
        Saved for this browsing session only. Accounts come later.
      </p>
      <FavoritesView />
    </Container>
  );
}
