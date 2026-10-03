import Image from "next/image";
import {
  ArrowDown,
  Camera,
  Footprints,
  Globe,
  ImageIcon,
  ScanSearch,
  Smartphone,
  Store,
  type LucideIcon,
} from "lucide-react";
import { formatXaf } from "@/lib/format";
import { products } from "@/data/products";
import { primaryImage } from "@/lib/products";
import { ComingSoonButton } from "./ComingSoonButton";
import { Container } from "./Container";

const sources: { label: string; icon: LucideIcon }[] = [
  { label: "On social media", icon: Smartphone },
  { label: "On another website", icon: Globe },
  { label: "In a screenshot", icon: ImageIcon },
  { label: "In real life", icon: Store },
];

// The scanned object is a sneaker, so every match shown is footwear.
const similarShoes = products.filter((p) => p.category === "shoes").slice(0, 2);

function FlowStep({ number, label }: { number: number; label: string }) {
  return (
    <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-muted">
      <span className="flex size-5 items-center justify-center rounded-full bg-cream text-[11px] text-ink">
        {number}
      </span>
      {label}
    </p>
  );
}

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

          {/* Illustration of the planned flow: photo of a shoe → visual search → similar shoes. */}
          <div aria-hidden="true" className="mx-auto w-full max-w-md">
            <div className="rounded-2xl bg-white p-4 text-ink">
              <FlowStep number={1} label="Photo of a shoe" />
              <div className="relative mt-2 aspect-[16/10] overflow-hidden rounded-xl bg-[#f2f2f2]">
                <Image
                  src="/images/categories/sneakers.webp"
                  alt=""
                  fill
                  sizes="420px"
                  className="object-cover"
                />
                <span className="absolute left-[18%] top-[12%] h-[76%] w-[64%] rounded-lg border-2 border-dashed border-deal" />
              </div>

              <div className="my-3 flex items-center gap-3">
                <span className="h-px flex-1 bg-line" />
                <span className="flex items-center gap-1.5 rounded-full bg-ink px-3 py-1.5 text-[11px] font-semibold text-white">
                  <ScanSearch className="size-3.5" />2 · Visual search
                  <ArrowDown className="size-3.5" />
                </span>
                <span className="h-px flex-1 bg-line" />
              </div>

              <FlowStep number={3} label="Similar shoes" />
              <ul className="mt-2 grid grid-cols-3 gap-2">
                {similarShoes.map((item) => (
                  <li
                    key={item.slug}
                    className="overflow-hidden rounded-lg border border-line"
                  >
                    <div className="relative aspect-square bg-[#f2f2f2]">
                      <Image
                        src={primaryImage(item).src}
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
                <li className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line bg-cream/60 p-2 text-center">
                  <Footprints className="size-5 text-muted" />
                  <span className="text-[11px] font-semibold">
                    More sneakers
                  </span>
                  <span className="text-[10px] text-muted">
                    Sorted by similarity
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
