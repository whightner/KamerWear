export interface NavLink {
  label: string;
  href: string;
}

export const mainNavigation: (NavLink & { highlight?: boolean })[] = [
  { label: "New In", href: "/shop?new=true" },
  { label: "Men", href: "/shop?gender=men" },
  { label: "Women", href: "/shop?gender=women" },
  { label: "Shoes", href: "/shop?category=shoes" },
  { label: "Accessories", href: "/shop?category=accessories" },
  { label: "Deals", href: "/shop?deals=true", highlight: true },
];

// Help pages and accounts arrive in later tasks; until then these links point
// to the homepage sections that describe them, or to future routes.
export const footerNavigation: { title: string; links: NavLink[] }[] = [
  {
    title: "Shop",
    links: [
      { label: "New In", href: "/shop?new=true" },
      { label: "Men", href: "/shop?gender=men" },
      { label: "Women", href: "/shop?gender=women" },
      { label: "Shoes", href: "/shop?category=shoes" },
      { label: "Deals", href: "/shop?deals=true" },
    ],
  },
  {
    title: "Help",
    links: [
      { label: "Delivery", href: "/#delivery" },
      { label: "Returns", href: "/#delivery" },
      { label: "Contact", href: "/#delivery" },
      { label: "FAQ", href: "/#delivery" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Profile", href: "/account" },
      { label: "Orders", href: "/orders" },
      { label: "Track order", href: "/orders/track" },
      { label: "Favorites", href: "/favorites" },
      { label: "Fit Profile", href: "/#smart-fit" },
    ],
  },
];
