import type { Metadata } from "next";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { Container } from "@/components/storefront/Container";
import { VisualSearch } from "@/components/visual-search/VisualSearch";

export const metadata: Metadata = {
  title: "Search by image — KamerWear",
  description: "Upload or take a photo of shoes, clothes or a bag and find similar items at KamerWear.",
};

export default function VisualSearchPage() {
  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: "Search by image" }]} />
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight text-ink">Search by image</h1>
      <p className="mb-6 mt-1 max-w-2xl text-sm text-muted">
        Seen something you like? Upload a photo or take one, and we&apos;ll find visually similar
        products in our catalog.
      </p>
      <VisualSearch />
    </Container>
  );
}
