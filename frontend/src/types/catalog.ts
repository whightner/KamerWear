// Presentation-only types. Catalog data types live in src/lib/api/types.ts.

/** A homepage category tile (marketing image + link to a filtered /shop view). */
export interface CategoryTile {
  slug: string;
  name: string;
  image: string;
  imageAlt: string;
  href: string;
  badge?: string;
}
