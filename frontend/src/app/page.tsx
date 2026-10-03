import { CategoryGrid } from "@/components/storefront/CategoryGrid";
import { FlashSale } from "@/components/storefront/FlashSale";
import { Footer } from "@/components/storefront/Footer";
import { Header } from "@/components/storefront/Header";
import { Hero } from "@/components/storefront/Hero";
import { ProductSection } from "@/components/storefront/ProductSection";
import { QuickActions } from "@/components/storefront/QuickActions";
import { SmartFitBanner } from "@/components/storefront/SmartFitBanner";
import { TrustSection } from "@/components/storefront/TrustSection";
import { VisualSearchBanner } from "@/components/storefront/VisualSearchBanner";
import { recommendedProducts } from "@/data/products";

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="flex-1">
        <Hero />
        <QuickActions />
        <CategoryGrid />
        <FlashSale />
        <ProductSection
          id="recommended"
          title="Recommended for you"
          subtitle="Popular picks this week"
          products={recommendedProducts}
        />
        <SmartFitBanner />
        <VisualSearchBanner />
        <TrustSection />
      </main>
      <Footer />
    </>
  );
}
