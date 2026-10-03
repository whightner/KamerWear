import { Zap } from "lucide-react";
import { CatalogUnavailable } from "@/components/catalog/CatalogUnavailable";
import type { ProductListItem } from "@/lib/api/types";
import { Container } from "./Container";
import { Countdown } from "./Countdown";
import { ProductCard } from "./ProductCard";
import { SectionHeading } from "./SectionHeading";

/** `products` is null when the catalog API could not be reached. */
export function FlashSale({
  products,
}: {
  products: ProductListItem[] | null;
}) {
  return (
    <section
      id="flash-sale"
      aria-labelledby="flash-sale-title"
      className="pt-14"
    >
      <Container>
        <div className="rounded-2xl border border-deal/20 bg-deal-soft p-5 lg:p-6">
          <SectionHeading
            id="flash-sale-title"
            title={
              <span className="flex items-center gap-2">
                <span className="flex size-8 items-center justify-center rounded-lg bg-deal text-white">
                  <Zap
                    className="size-[18px] fill-current"
                    aria-hidden="true"
                  />
                </span>
                Flash Sale
              </span>
            }
            action={{ label: "View all", href: "/shop?deals=true" }}
          >
            <div className="flex items-center gap-2.5">
              <span className="text-sm font-medium text-muted">Ends in</span>
              <Countdown />
            </div>
          </SectionHeading>

          {products === null ? (
            <CatalogUnavailable compact />
          ) : (
            <ul className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
              {products.map((product) => (
                <li key={product.slug}>
                  <ProductCard
                    product={product}
                    imageSizes="(min-width: 1280px) 210px, (min-width: 768px) 33vw, 50vw"
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      </Container>
    </section>
  );
}
