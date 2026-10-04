import { CategoryGrid } from "@/components/storefront/CategoryGrid";
import { FlashSale } from "@/components/storefront/FlashSale";
import { Hero } from "@/components/storefront/Hero";
import { ProductSection } from "@/components/storefront/ProductSection";
import { QuickActions } from "@/components/storefront/QuickActions";
import { SmartFitBanner } from "@/components/storefront/SmartFitBanner";
import { TrustSection } from "@/components/storefront/TrustSection";
import { VisualSearchBanner } from "@/components/storefront/VisualSearchBanner";
import { connection } from "next/server";
import { CatalogApiError, getProducts } from "@/lib/api/catalog";
import type { ProductListItem } from "@/lib/api/types";

/** Product rows for the homepage; null when the catalog API failed. */
async function loadSafely(
  load: () => ReturnType<typeof getProducts>,
): Promise<ProductListItem[] | null> {
  try {
    return (await load()).items;
  } catch (error) {
    if (!(error instanceof CatalogApiError)) throw error;
    console.error("Homepage catalog request failed:", error);
    return null;
  }
}

export default async function HomePage() {
  // Catalog data is read at request time, never baked in at build time.
  await connection();
  const [flashSale, recommended, sneakers] = await Promise.all([
    // Biggest discounts first: deterministic and fitting for a sale row.
    loadSafely(() =>
      getProducts({ on_sale: true, sort: "discount", limit: 6 }),
    ),
    // Rule-based "recommended" order from the API (featured first), not personalised.
    loadSafely(() => getProducts({ sort: "recommended", limit: 8 })),
    loadSafely(() => getProducts({ category: "shoes", limit: 2 })),
  ]);

  return (
    <>
      <Hero />
      <QuickActions />
      <CategoryGrid />
      <FlashSale products={flashSale} />
      <ProductSection
        id="recommended"
        title="Popular picks"
        subtitle="Featured items from our catalog"
        products={recommended}
        viewAllHref="/shop"
      />
      <SmartFitBanner />
      <VisualSearchBanner similarShoes={sneakers ?? []} />
      <TrustSection />
    </>
  );
}
