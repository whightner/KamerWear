import type { ProductListItem } from "@/lib/api/types";
import { Container } from "./Container";
import { CatalogUnavailable } from "@/components/catalog/CatalogUnavailable";
import { ProductCard } from "./ProductCard";
import { SectionHeading } from "./SectionHeading";

interface ProductSectionProps {
  id: string;
  title: string;
  subtitle?: string;
  /** Null when the catalog API could not be reached. */
  products: ProductListItem[] | null;
  viewAllHref: string;
}

export function ProductSection({
  id,
  title,
  subtitle,
  products,
  viewAllHref,
}: ProductSectionProps) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="pt-14">
      <Container>
        <SectionHeading
          id={`${id}-title`}
          title={title}
          subtitle={subtitle}
          action={{ label: "View all", href: viewAllHref }}
        />
        {products === null ? (
          <CatalogUnavailable compact />
        ) : (
          <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
            {products.map((product) => (
              <li key={product.slug}>
                <ProductCard
                  product={product}
                  imageSizes="(min-width: 1024px) 300px, (min-width: 768px) 33vw, 50vw"
                />
              </li>
            ))}
          </ul>
        )}
      </Container>
    </section>
  );
}
