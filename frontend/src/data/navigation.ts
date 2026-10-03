export interface NavLink {
  label: string;
  href: string;
}

// Pages for these links come in later tasks; for now they point at sections of the homepage.
export const mainNavigation: (NavLink & { highlight?: boolean })[] = [
  { label: "New In", href: "#recommended" },
  { label: "Men", href: "#categories" },
  { label: "Women", href: "#categories" },
  { label: "Shoes", href: "#categories" },
  { label: "Accessories", href: "#categories" },
  { label: "Deals", href: "#flash-sale", highlight: true },
];

export const footerNavigation: { title: string; links: NavLink[] }[] = [
  {
    title: "Shop",
    links: [
      { label: "New In", href: "#recommended" },
      { label: "Men", href: "#categories" },
      { label: "Women", href: "#categories" },
      { label: "Shoes", href: "#categories" },
      { label: "Deals", href: "#flash-sale" },
    ],
  },
  {
    title: "Help",
    links: [
      { label: "Delivery", href: "#delivery" },
      { label: "Returns", href: "#delivery" },
      { label: "Contact", href: "#delivery" },
      { label: "FAQ", href: "#delivery" },
    ],
  },
  {
    title: "Account",
    links: [
      { label: "Profile", href: "#" },
      { label: "Orders", href: "#" },
      { label: "Favorites", href: "#" },
      { label: "Fit Profile", href: "#smart-fit" },
    ],
  },
];
