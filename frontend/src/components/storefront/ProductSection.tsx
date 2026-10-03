import type { Product } from "@/types/catalog";
import { Container } from "./Container";
import { ProductCard } from "./ProductCard";
import { SectionHeading } from "./SectionHeading";

interface ProductSectionProps {
  id: string;
  title: string;
  subtitle?: string;
  products: Product[];
}

export function ProductSection({
  id,
  title,
  subtitle,
  products,
}: ProductSectionProps) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="pt-14">
      <Container>
        <SectionHeading
          id={`${id}-title`}
          title={title}
          subtitle={subtitle}
          action={{ label: "View all", href: "#recommended" }}
        />
        <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-4">
          {products.map((product) => (
            <li key={product.id}>
              <ProductCard
                product={product}
                imageSizes="(min-width: 1024px) 300px, (min-width: 768px) 33vw, 50vw"
              />
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
