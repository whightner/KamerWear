import type { Category } from "@/types/catalog";

// Homepage category tiles; each opens a filtered /shop view.
export const categories: Category[] = [
  {
    slug: "sneakers",
    name: "Sneakers",
    image: "/images/categories/sneakers.webp",
    imageAlt: "Black knit running sneaker",
    href: "/shop?category=shoes",
  },
  {
    slug: "men",
    name: "Men",
    image: "/images/categories/men.webp",
    imageAlt: "Smiling man in a red relaxed T-shirt outdoors",
    href: "/shop?gender=men",
  },
  {
    slug: "women",
    name: "Women",
    image: "/images/categories/women.webp",
    imageAlt: "Woman in an oversized pastel T-shirt and denim shorts",
    href: "/shop?gender=women",
  },
  {
    slug: "streetwear",
    name: "Streetwear",
    image: "/images/categories/streetwear.webp",
    imageAlt: "Man in a black beanie and green jacket on a city street",
    href: "/shop?q=streetwear",
  },
  {
    slug: "accessories",
    name: "Accessories",
    image: "/images/categories/accessories.webp",
    imageAlt: "Man wearing a cream knit beanie in the sun",
    href: "/shop?category=accessories",
  },
  {
    slug: "deals",
    name: "Deals",
    image: "/images/categories/deals.webp",
    imageAlt: "Woman in an orange zip-up jacket",
    href: "/shop?deals=true",
    badge: "On sale now",
  },
];
