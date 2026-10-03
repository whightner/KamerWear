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

// Delivery and FAQ still point to the homepage delivery section; returns and
// contact have their own help pages.
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
      { label: "Returns", href: "/help/returns" },
      { label: "Contact", href: "/help/contact" },
      { label: "FAQ", href: "/#delivery" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "My account", href: "/account" },
      { label: "Profile", href: "/account/profile" },
      { label: "Orders", href: "/orders" },
      { label: "Returns", href: "/account/returns" },
      { label: "Support", href: "/support" },
      { label: "Track order", href: "/orders/track" },
      { label: "Favorites", href: "/favorites" },
      { label: "Fit Profile", href: "/account/fit-profile" },
    ],
  },
];
