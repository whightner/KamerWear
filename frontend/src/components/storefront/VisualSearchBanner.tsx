import Image from "next/image";
import {
  Camera,
  Globe,
  ImageIcon,
  ScanSearch,
  Smartphone,
  Store,
  type LucideIcon,
} from "lucide-react";
import { formatXaf } from "@/lib/format";
import { products } from "@/data/products";
import { ComingSoonButton } from "./ComingSoonButton";
import { Container } from "./Container";

const sources: { label: string; icon: LucideIcon }[] = [
  { label: "On social media", icon: Smartphone },
  { label: "On another website", icon: Globe },
  { label: "In a screenshot", icon: ImageIcon },
  { label: "In real life", icon: Store },
];

const similarItems = products.filter((p) =>
  ["urban-runner-02", "flex-knit-runner", "city-bomber-jacket"].includes(
    p.slug,
  ),
);

export function VisualSearchBanner() {
  return (
    <section
      id="visual-search"
      aria-labelledby="visual-search-title"
      className="pt-14"
    >
      <Container>
        <div className="grid items-center gap-10 overflow-hidden rounded-2xl bg-ink px-8 py-12 text-white lg:grid-cols-2 lg:px-14">
          <div>
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-gold">
              <ScanSearch className="size-4" aria-hidden="true" />
              Visual search
            </p>
            <h2
              id="visual-search-title"
              className="mt-3 text-4xl font-black uppercase tracking-tight lg:text-5xl"
            >
              See it. Scan it. Find it.
            </h2>
            <p className="mt-4 max-w-lg text-white/75">
              Spotted shoes or an outfit you love? Upload or take a photo and
              KamerWear will show visually similar items you can buy here.
            </p>

            <ul className="mt-6 grid max-w-lg grid-cols-2 gap-3">
              {sources.map(({ label, icon: Icon }) => (
                <li
                  key={label}
                  className="flex items-center gap-2.5 rounded-lg border border-white/15 px-3 py-2.5 text-sm"
                >
                  <Icon className="size-4 text-gold" aria-hidden="true" />
                  {label}
                </li>
              ))}
            </ul>

            <div className="mt-8">
              <ComingSoonButton
                className="inline-flex h-12 items-center gap-2 rounded-lg bg-white px-6 text-sm font-semibold text-ink hover:bg-cream"
                message="Search by image is in development and will be available soon."
                messageClassName="text-white/75"
              >
                <Camera className="size-4" aria-hidden="true" />
                Search by Image
              </ComingSoonButton>
            </div>
          </div>

          {/* Illustration of the planned flow, built from local demo products. */}
          <div aria-hidden="true" className="mx-auto w-full max-w-md">
            <div className="rounded-2xl bg-white p-4 text-ink">
              <div className="relative aspect-[4/3] overflow-hidden rounded-xl bg-[#f6f6f6]">
                <Image
                  src="/images/categories/sneakers.webp"
                  alt=""
                  fill
                  sizes="420px"
                  className="object-cover"
                />
                <span className="absolute left-[22%] top-[24%] h-[52%] w-[56%] rounded-lg border-2 border-dashed border-deal" />
                <span className="absolute left-3 top-3 rounded-md bg-ink px-2 py-1 text-[11px] font-semibold text-white">
                  Your photo
                </span>
              </div>
              <p className="mt-4 text-xs font-bold uppercase tracking-wider text-muted">
                Similar items
              </p>
              <ul className="mt-2 grid grid-cols-3 gap-2">
                {similarItems.map((item) => (
                  <li
                    key={item.id}
                    className="overflow-hidden rounded-lg border border-line"
                  >
                    <div className="relative aspect-square bg-[#f3f3f1]">
                      <Image
                        src={item.image}
                        alt=""
                        fill
                        sizes="130px"
                        className="object-cover"
                      />
                    </div>
                    <p className="truncate px-2 pt-1.5 text-[11px] font-semibold">
                      {item.name}
                    </p>
                    <p className="px-2 pb-2 text-[11px] font-bold text-deal">
                      {formatXaf(item.price)}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
