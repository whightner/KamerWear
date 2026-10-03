import Image from "next/image";
import Link from "next/link";
import { categories } from "@/data/categories";
import { Container } from "./Container";
import { SectionHeading } from "./SectionHeading";

export function CategoryGrid() {
  return (
    <section
      id="categories"
      aria-labelledby="categories-title"
      className="pt-14"
    >
      <Container>
        <SectionHeading id="categories-title" title="Shop by category" />
        <ul className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
          {categories.map((category) => (
            <li key={category.slug}>
              <Link
                href={category.href}
                className="group relative block aspect-[4/5] overflow-hidden rounded-xl bg-white"
              >
                <Image
                  src={category.image}
                  alt={category.imageAlt}
                  fill
                  sizes="(min-width: 1024px) 200px, (min-width: 640px) 33vw, 50vw"
                  className="object-cover transition duration-300 group-hover:scale-105"
                />
                <span className="absolute inset-x-0 bottom-0 h-1/2 bg-linear-to-t from-black/65 to-transparent" />
                {category.badge && (
                  <span className="absolute left-3 top-3 rounded-md bg-deal px-2 py-1 text-[11px] font-bold text-white">
                    {category.badge}
                  </span>
                )}
                <span className="absolute bottom-3 left-3 text-base font-bold text-white">
                  {category.name}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </Container>
    </section>
  );
}
