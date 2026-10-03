import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Headphones, RotateCcw, Star, Truck } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { ProductDetail } from "@/components/product/ProductDetail";
import { Container } from "@/components/storefront/Container";
import { getProduct, products } from "@/data/products";
import { CATEGORY_OPTIONS } from "@/lib/catalog";
import { similarProducts } from "@/lib/products";

export function generateStaticParams() {
  return products.map((product) => ({ slug: product.slug }));
}

export async function generateMetadata({
  params,
}: PageProps<"/product/[slug]">): Promise<Metadata> {
  const product = getProduct((await params).slug);
  if (!product) return { title: "Product not found — KamerWear" };
  return {
    title: `${product.name} — KamerWear`,
    description: product.description,
  };
}

// Help pages arrive in a later task; these links point to their future routes.
const services = [
  {
    title: "Delivery",
    text: "Delivery to supported Cameroon cities. Fees shown at checkout.",
    href: "/help/delivery",
    icon: Truck,
  },
  {
    title: "Returns",
    text: "Return eligible items under our returns policy.",
    href: "/help/returns",
    icon: RotateCcw,
  },
  {
    title: "Customer support",
    text: "Questions about sizing or delivery? Contact our team.",
    href: "/help/contact",
    icon: Headphones,
  },
];

export default async function ProductPage({
  params,
}: PageProps<"/product/[slug]">) {
  const product = getProduct((await params).slug);
  if (!product) notFound();

  const category = CATEGORY_OPTIONS.find((o) => o.value === product.category)!;

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          { label: "Shop", href: "/shop" },
          { label: category.label, href: `/shop?category=${category.value}` },
          { label: product.name },
        ]}
      />

      <div className="mt-6">
        <ProductDetail
          product={product}
          similar={similarProducts(product, products)}
        />
      </div>

      <div className="mt-14 grid gap-6 lg:grid-cols-12">
        <section aria-labelledby="details-heading" className="lg:col-span-7">
          <h2 id="details-heading" className="text-xl font-extrabold text-ink">
            Product details
          </h2>
          <p className="mt-3 max-w-2xl leading-relaxed text-muted">
            {product.description}
          </p>
          <dl className="mt-5 grid max-w-xl grid-cols-[auto_1fr] gap-x-8 gap-y-2 text-sm">
            <dt className="text-muted">Category</dt>
            <dd className="text-ink">
              {category.label} · {product.type}
            </dd>
            <dt className="text-muted">Colours</dt>
            <dd className="text-ink">
              {product.colors.map((c) => c.name).join(", ")}
            </dd>
            <dt className="text-muted">Sizes</dt>
            <dd className="text-ink">
              {product.sizes.length
                ? `${product.category === "shoes" ? "EU " : ""}${product.sizes.join(", ")}`
                : "One size"}
            </dd>
            <dt className="text-muted">Smart Fit</dt>
            <dd className="text-ink">
              {product.smartFit ? "Available" : "Not available"}
            </dd>
          </dl>
        </section>

        <section
          id="reviews"
          aria-labelledby="reviews-heading"
          className="scroll-mt-32 rounded-2xl border border-line bg-white p-6 lg:col-span-5"
        >
          <h2 id="reviews-heading" className="text-xl font-extrabold text-ink">
            Reviews
          </h2>
          <div className="mt-4 flex items-center gap-4">
            <p className="text-5xl font-black text-ink">
              {product.rating.toFixed(1)}
            </p>
            <div>
              <p
                className="flex gap-0.5"
                aria-label={`${product.rating.toFixed(1)} out of 5 stars`}
              >
                {[1, 2, 3, 4, 5].map((n) => (
                  <Star
                    key={n}
                    aria-hidden="true"
                    className={`size-4 ${n <= Math.round(product.rating) ? "fill-gold text-gold" : "text-line"}`}
                  />
                ))}
              </p>
              <p className="mt-1 text-sm text-muted">
                {product.reviewCount} reviews
              </p>
            </div>
          </div>
          <p className="mt-4 text-xs text-muted">
            Demo rating summary. Written reviews arrive with customer accounts.
          </p>
        </section>
      </div>

      <ul className="mt-10 grid gap-4 md:grid-cols-3">
        {services.map(({ title, text, href, icon: Icon }) => (
          <li
            key={title}
            className="flex gap-3 rounded-xl border border-line bg-white p-4"
          >
            <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-cream">
              <Icon className="size-5 text-ink" aria-hidden="true" />
            </span>
            <span>
              <span className="block text-sm font-bold text-ink">{title}</span>
              <span className="mt-0.5 block text-sm text-muted">{text}</span>
              {/* Plain link: the help page doesn't exist yet, so nothing is prefetched. */}
              <a
                href={href}
                className="mt-1 inline-block text-xs font-semibold text-ink underline underline-offset-2"
              >
                Learn more
              </a>
            </span>
          </li>
        ))}
      </ul>
    </Container>
  );
}
