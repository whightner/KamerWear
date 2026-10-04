import {
  ChevronRight,
  Ruler,
  ScanSearch,
  Truck,
  Zap,
  type LucideIcon,
} from "lucide-react";
import { Container } from "./Container";

interface QuickAction {
  title: string;
  description: string;
  href: string;
  icon: LucideIcon;
  iconClassName: string;
}

const actions: QuickAction[] = [
  {
    title: "Scan & Find",
    description:
      "Found an outfit somewhere else? Upload a photo and find similar products.",
    href: "#visual-search",
    icon: ScanSearch,
    iconClassName: "bg-ink text-white",
  },
  {
    title: "Flash Deals",
    description: "Limited-time prices on selected fashion.",
    href: "#flash-sale",
    icon: Zap,
    iconClassName: "bg-deal text-white",
  },
  {
    title: "Smart Fit",
    description: "Get personal size recommendations.",
    href: "#smart-fit",
    icon: Ruler,
    iconClassName: "bg-fit text-white",
  },
  {
    title: "Fast Delivery",
    description: "Delivery to supported Cameroon cities.",
    href: "#delivery",
    icon: Truck,
    iconClassName: "bg-gold text-ink",
  },
];

export function QuickActions() {
  return (
    <section aria-label="Shopping shortcuts" className="pt-4">
      <Container>
        <ul className="grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
          {actions.map(
            ({ title, description, href, icon: Icon, iconClassName }) => (
              <li key={title} className="bg-white">
                <a
                  href={href}
                  className="group flex h-full items-center gap-4 p-5 hover:bg-cream/70"
                >
                  <span
                    className={`flex size-11 shrink-0 items-center justify-center rounded-lg ${iconClassName}`}
                  >
                    <Icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-sm font-bold text-ink">
                      {title}
                    </span>
                    <span className="mt-0.5 block text-xs leading-snug text-muted">
                      {description}
                    </span>
                  </span>
                  <ChevronRight
                    className="size-4 shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-ink"
                    aria-hidden="true"
                  />
                </a>
              </li>
            ),
          )}
        </ul>
      </Container>
    </section>
  );
}
