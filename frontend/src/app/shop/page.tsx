import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";
import { ChevronLeft, ChevronRight, Search, X } from "lucide-react";
import { Breadcrumbs } from "@/components/catalog/Breadcrumbs";
import { CatalogFilters } from "@/components/catalog/CatalogFilters";
import { CatalogUnavailable } from "@/components/catalog/CatalogUnavailable";
import { SortSelect } from "@/components/catalog/SortSelect";
import { Container } from "@/components/storefront/Container";
import { ProductCard } from "@/components/storefront/ProductCard";
import { CatalogApiError, getCategories, getProducts } from "@/lib/api/catalog";
import type { Category, PaginatedProducts } from "@/lib/api/types";
import {
  activeFilterChips,
  catalogHref,
  catalogParams,
  catalogTitle,
  parseCatalogParams,
  toProductQuery,
  type CatalogFilters as Filters,
} from "@/lib/catalog";

export async function generateMetadata({
  searchParams,
}: PageProps<"/shop">): Promise<Metadata> {
  const filters = parseCatalogParams(await searchParams);
  const categories = await getCategories().catch((error) => {
    if (error instanceof CatalogApiError) return [];
    throw error;
  });
  return { title: `${catalogTitle(filters, categories)} — KamerWear` };
}

type CatalogResult =
  | { ok: true; categories: Category[]; page: PaginatedProducts }
  | { ok: false; categories: Category[] };

async function loadCatalog(filters: Filters): Promise<CatalogResult> {
  // The API does the filtering, search, sorting and pagination.
  const [categories, page] = await Promise.allSettled([
    getCategories(),
    getProducts(toProductQuery(filters)),
  ]);
  for (const result of [categories, page]) {
    // Only API failures become the "unavailable" state; anything else is a bug.
    if (
      result.status === "rejected" &&
      !(result.reason instanceof CatalogApiError)
    ) {
      throw result.reason;
    }
  }
  const categoryList =
    categories.status === "fulfilled" ? categories.value : [];
  if (page.status === "rejected") {
    console.error("Catalog request failed:", page.reason);
    return { ok: false, categories: categoryList };
  }
  return { ok: true, categories: categoryList, page: page.value };
}

export default async function ShopPage({ searchParams }: PageProps<"/shop">) {
  const filters = parseCatalogParams(await searchParams);
  const result = await loadCatalog(filters);
  const title = catalogTitle(filters, result.categories);
  const chips = activeFilterChips(filters, result.categories);

  return (
    <Container className="pb-16 pt-6">
      <Breadcrumbs
        items={[
          { label: "Home", href: "/" },
          title === "Shop"
            ? { label: "Shop" }
            : { label: "Shop", href: "/shop" },
          ...(title === "Shop" ? [] : [{ label: title }]),
        ]}
      />

      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">
            {title}
          </h1>
          {result.ok && (
            <p className="mt-1 text-sm text-muted" role="status">
              {result.page.total}{" "}
              {result.page.total === 1 ? "product" : "products"}
            </p>
          )}
        </div>

        {/* Searching keeps the other filters: they ride along as hidden fields. */}
        <Form
          action="/shop"
          role="search"
          className="flex h-10 w-full max-w-sm items-center rounded-lg border border-line bg-white pl-3 focus-within:border-ink"
        >
          <Search className="size-4 shrink-0 text-muted" aria-hidden="true" />
          <label htmlFor="catalog-search" className="sr-only">
            Search the catalog
          </label>
          <input
            id="catalog-search"
            name="q"
            type="search"
            defaultValue={filters.q}
            placeholder="Search: runner, hoodie…"
            className="h-full min-w-0 flex-1 bg-transparent px-2.5 text-sm outline-none placeholder:text-muted"
          />
          {[...catalogParams({ ...filters, q: "", page: 1 })].map(
            ([name, value]) => (
              <input key={name} type="hidden" name={name} value={value} />
            ),
          )}
          <button
            type="submit"
            className="h-full rounded-r-lg bg-ink px-4 text-sm font-semibold text-white"
          >
            Search
          </button>
        </Form>
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-[240px_1fr] lg:items-start">
        <aside aria-label="Product filters" className="lg:sticky lg:top-32">
          <CatalogFilters
            filters={filters}
            categories={result.categories}
            activeCount={chips.length}
          />
        </aside>

        <section aria-label="Products">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <ul className="flex flex-wrap gap-2" aria-label="Active filters">
              {chips.map((chip) => (
                <li key={chip.label}>
                  <Link
                    href={chip.href}
                    scroll={false}
                    aria-label={`Remove filter ${chip.label}`}
                    className="flex h-8 items-center gap-1.5 rounded-full border border-line bg-white pl-3 pr-2 text-xs font-semibold text-ink hover:border-ink/40"
                  >
                    {chip.label}
                    <X className="size-3.5 text-muted" aria-hidden="true" />
                  </Link>
                </li>
              ))}
            </ul>
            <SortSelect filters={filters} />
          </div>

          {!result.ok ? (
            <CatalogUnavailable />
          ) : result.page.items.length > 0 ? (
            <>
              <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
                {result.page.items.map((product) => (
                  <li key={product.id}>
                    <ProductCard
                      product={product}
                      imageSizes="(min-width: 1280px) 260px, (min-width: 768px) 30vw, 50vw"
                    />
                  </li>
                ))}
              </ul>
              <Pagination filters={filters} page={result.page} />
            </>
          ) : (
            <div className="rounded-xl border border-dashed border-line bg-white px-6 py-16 text-center">
              <p className="text-lg font-bold text-ink">
                {filters.page > 1 && result.page.total > 0
                  ? "This page is empty"
                  : "No products match these filters"}
              </p>
              <p className="mt-1 text-sm text-muted">
                Try removing a filter or searching for something broader.
              </p>
              <Link
                href="/shop"
                className="mt-5 inline-flex h-10 items-center rounded-lg bg-ink px-5 text-sm font-semibold text-white"
              >
                Clear all filters
              </Link>
            </div>
          )}
        </section>
      </div>
    </Container>
  );
}

/** Previous / Next pagination that keeps every filter in the URL. */
function Pagination({
  filters,
  page,
}: {
  filters: Filters;
  page: PaginatedProducts;
}) {
  const pageCount = Math.max(1, Math.ceil(page.total / page.limit));
  if (pageCount <= 1) return null;
  const current = Math.floor(page.offset / page.limit) + 1;
  const linkClass =
    "inline-flex h-10 items-center gap-1 rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-ink/40";
  const disabledClass =
    "inline-flex h-10 items-center gap-1 rounded-lg border border-line bg-cream/60 px-4 text-sm font-semibold text-muted";

  return (
    <nav
      aria-label="Pagination"
      className="mt-8 flex items-center justify-center gap-3"
    >
      {current > 1 ? (
        <Link
          href={catalogHref({ ...filters, page: current - 1 })}
          className={linkClass}
        >
          <ChevronLeft className="size-4" aria-hidden="true" />
          Previous
        </Link>
      ) : (
        <span className={disabledClass} aria-disabled="true">
          <ChevronLeft className="size-4" aria-hidden="true" />
          Previous
        </span>
      )}
      <p className="text-sm text-muted" aria-current="page">
        Page <span className="font-semibold text-ink">{current}</span> of{" "}
        {pageCount}
      </p>
      {current < pageCount ? (
        <Link
          href={catalogHref({ ...filters, page: current + 1 })}
          className={linkClass}
        >
          Next
          <ChevronRight className="size-4" aria-hidden="true" />
        </Link>
      ) : (
        <span className={disabledClass} aria-disabled="true">
          Next
          <ChevronRight className="size-4" aria-hidden="true" />
        </span>
      )}
    </nav>
  );
}
