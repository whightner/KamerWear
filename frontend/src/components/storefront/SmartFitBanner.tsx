import Image from "next/image";
import { Ruler } from "lucide-react";
import { ComingSoonButton } from "./ComingSoonButton";
import { Container } from "./Container";

const steps = [
  {
    title: "Enter your height",
    text: "A quick starting point for your profile.",
  },
  {
    title: "Take guided photos",
    text: "Front and side photos, with on-screen tips.",
  },
  {
    title: "Receive estimated sizes",
    text: "Recommended sizes for each product, with a confidence level.",
  },
  {
    title: "Confirm before saving",
    text: "Adjust anything. Nothing is saved until you confirm.",
  },
];

export function SmartFitBanner() {
  return (
    <section id="smart-fit" aria-labelledby="smart-fit-title" className="pt-14">
      <Container>
        <div className="grid overflow-hidden rounded-2xl bg-fit-soft lg:grid-cols-12">
          <div className="relative min-h-[360px] lg:col-span-5">
            <Image
              src="/images/features/smart-fit.webp"
              alt="Man standing on a beach in a white T-shirt and dark jeans"
              fill
              sizes="(min-width: 1024px) 520px, 100vw"
              className="object-cover object-top"
            />
            <div className="absolute bottom-5 left-5 right-5 rounded-xl bg-white/95 p-4 shadow-[0_10px_30px_rgba(27,26,25,0.15)] sm:right-auto sm:w-64">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted">
                Your estimate
              </p>
              <div className="mt-2 flex items-end justify-between">
                <div>
                  <p className="text-xs text-muted">Tops</p>
                  <p className="text-xl font-extrabold text-ink">M</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Trousers</p>
                  <p className="text-xl font-extrabold text-ink">32</p>
                </div>
                <div>
                  <p className="text-xs text-muted">Shoes</p>
                  <p className="text-xl font-extrabold text-ink">43</p>
                </div>
              </div>
              <div className="mt-3">
                <div className="flex justify-between text-[11px] font-semibold">
                  <span className="text-fit">Confidence: high</span>
                  <span className="text-muted">Example</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-fit/15">
                  <div className="h-full w-4/5 rounded-full bg-fit" />
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-col justify-center px-8 py-10 lg:col-span-7 lg:px-14">
            <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-fit">
              <Ruler className="size-4" aria-hidden="true" />
              Smart Fit
            </p>
            <h2
              id="smart-fit-title"
              className="mt-3 text-3xl font-extrabold tracking-tight text-ink lg:text-4xl"
            >
              Not sure about your size?
            </h2>
            <p className="mt-3 max-w-xl text-muted">
              Create a Fit Profile and get recommended sizes for each product.
              Recommendations are estimates based on your inputs, so you always
              review and confirm the result.
            </p>

            <ol className="mt-7 grid gap-4 sm:grid-cols-2">
              {steps.map((step, index) => (
                <li key={step.title} className="flex gap-3">
                  <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-fit text-sm font-bold text-white">
                    {index + 1}
                  </span>
                  <span>
                    <span className="block text-sm font-bold text-ink">
                      {step.title}
                    </span>
                    <span className="block text-sm text-muted">
                      {step.text}
                    </span>
                  </span>
                </li>
              ))}
            </ol>

            <div className="mt-8">
              <ComingSoonButton
                className="inline-flex h-12 items-center gap-2 rounded-lg bg-fit px-6 text-sm font-semibold text-white hover:bg-fit-dark"
                message="Fit Profiles are coming soon to KamerWear."
                messageClassName="text-fit-dark"
              >
                <Ruler className="size-4" aria-hidden="true" />
                Create My Fit Profile
              </ComingSoonButton>
            </div>
          </div>
        </div>
      </Container>
    </section>
  );
}
