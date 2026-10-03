import type { Category } from "@/types/catalog";

// Mock categories for the storefront demo. Category pages come in a later task.
export const categories: Category[] = [
  {
    slug: "sneakers",
    name: "Sneakers",
    image: "/images/categories/sneakers.webp",
    imageAlt: "Black knit running sneaker",
    href: "#recommended",
  },
  {
    slug: "men",
    name: "Men",
    image: "/images/categories/men.webp",
    imageAlt: "Smiling man in a red relaxed T-shirt outdoors",
    href: "#recommended",
  },
  {
    slug: "women",
    name: "Women",
    image: "/images/categories/women.webp",
    imageAlt: "Woman in an oversized pastel T-shirt and denim shorts",
    href: "#recommended",
  },
  {
    slug: "streetwear",
    name: "Streetwear",
    image: "/images/categories/streetwear.webp",
    imageAlt: "Man in a black beanie and green jacket on a city street",
    href: "#recommended",
  },
  {
    slug: "accessories",
    name: "Accessories",
    image: "/images/categories/accessories.webp",
    imageAlt: "Man wearing a cream knit beanie in the sun",
    href: "#recommended",
  },
  {
    slug: "deals",
    name: "Deals",
    image: "/images/categories/deals.webp",
    imageAlt: "Woman in an orange zip-up jacket",
    href: "#flash-sale",
    badge: "Up to 40% off",
  },
];
