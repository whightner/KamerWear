import Image from "next/image";
import Link from "next/link";
import { ArrowRight, Ruler } from "lucide-react";
import { Container } from "./Container";

export function Hero() {
  return (
    <section aria-labelledby="hero-title" className="pt-6">
      <Container>
        <div className="grid overflow-hidden rounded-2xl bg-sand lg:grid-cols-12">
          <div className="flex flex-col justify-center px-8 py-12 lg:col-span-5 lg:px-14 lg:py-16">
            <p className="text-xs font-bold tracking-[0.25em] text-deal-dark">
              NEW SEASON • 2026
            </p>
            <h1
              id="hero-title"
              className="mt-4 text-5xl font-black uppercase leading-[0.95] tracking-tight text-ink xl:text-[4.25rem]"
            >
              Style that
              <br />
              fits you.
            </h1>
            <p className="mt-5 max-w-sm text-lg text-muted">
              Discover fashion, smarter sizing and fast local delivery.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/shop?new=true"
                className="inline-flex h-12 items-center gap-2 rounded-lg bg-ink px-6 text-sm font-semibold text-white hover:bg-black"
              >
                Shop New Arrivals
                <ArrowRight className="size-4" aria-hidden="true" />
              </Link>
              <Link
                href="/#smart-fit"
                className="inline-flex h-12 items-center gap-2 rounded-lg border border-ink/80 bg-white/40 px-6 text-sm font-semibold text-ink hover:bg-white"
              >
                <Ruler className="size-4" aria-hidden="true" />
                Find My Size
              </Link>
            </div>
          </div>

          <div className="relative grid min-h-[420px] grid-cols-5 gap-3 p-3 lg:col-span-7 lg:min-h-[540px]">
            <div className="relative col-span-3 overflow-hidden rounded-xl">
              <Image
                src="/images/hero/hero-main.webp"
                alt="Smiling man in a relaxed black T-shirt by the sea"
                fill
                loading="eager"
                fetchPriority="high"
                sizes="(min-width: 1024px) 34vw, 60vw"
                className="object-cover object-top"
              />
            </div>
            <div className="relative col-span-2 overflow-hidden rounded-xl">
              <Image
                src="/images/hero/hero-secondary.webp"
                alt="Smiling woman in a sage T-shirt and jeans on the beach"
                fill
                loading="eager"
                sizes="(min-width: 1024px) 23vw, 40vw"
                className="object-cover object-top"
              />
            </div>

            <div className="absolute bottom-7 left-7 rounded-xl bg-white p-4 shadow-[0_10px_30px_rgba(27,26,25,0.15)]">
              <p className="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-fit">
                <Ruler className="size-3.5" aria-hidden="true" />
                Smart Fit
              </p>
              <p className="mt-1 text-sm font-semibold text-ink">
                Recommended size: M
              </p>
              <p className="text-xs text-muted">
                Example · estimated, confirm before you buy
              </p>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
