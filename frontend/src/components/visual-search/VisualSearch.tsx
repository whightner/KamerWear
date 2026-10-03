"use client";

import { useEffect, useId, useRef, useState, type DragEvent } from "react";
import Link from "next/link";
import { Camera, ImageUp, Loader2, RefreshCw, ScanSearch, X } from "lucide-react";
import { ProductCard } from "@/components/storefront/ProductCard";
import type { VisualSearchResponse } from "@/lib/visual-search/types";

const ACCEPTED = ["image/jpeg", "image/png", "image/webp"];
const MAX_BYTES = 8 * 1024 * 1024;
const STORAGE_KEY = "kw-visual-search-results";

const MESSAGES: Record<string, string> = {
  invalid_image: "This file isn't a readable image. Please choose a JPEG, PNG or WebP photo.",
  unsupported_image_type: "Please choose a JPEG, PNG or WebP photo. HEIC photos aren't supported yet.",
  image_too_large: "This photo is too large. Please use one under 8 MB.",
  too_many_searches: "You've searched a lot in a short time. Please wait a minute and try again.",
  visual_search_unavailable: "Visual search is unavailable right now. Please try again later, or browse the shop.",
  visual_search_not_ready: "Visual search isn't ready yet: our product photos are still being prepared.",
  no_searchable_products: "No products are available for visual search right now.",
  unavailable: "We couldn't reach KamerWear right now. Please check your connection and try again.",
};

type Status =
  | { kind: "idle" }
  | { kind: "searching" }
  | { kind: "error"; message: string }
  | { kind: "done"; result: VisualSearchResponse };

export function VisualSearch() {
  const fileId = useId();
  const cameraId = useId();
  const fileInput = useRef<HTMLInputElement>(null);
  const cameraInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>({ kind: "idle" });
  const [dragging, setDragging] = useState(false);
  const [restored, setRestored] = useState(false);

  // Coming back from a product page: show the previous results (results only;
  // the photo itself is never stored anywhere).
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        // eslint-disable-next-line react-hooks/set-state-in-effect -- one-time restore on mount
        setStatus({ kind: "done", result: JSON.parse(saved) as VisualSearchResponse });
        setRestored(true);
      }
    } catch {
      /* storage unavailable: start fresh */
    }
  }, []);

  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- preview follows the chosen file
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function choose(candidate: File | undefined | null) {
    if (!candidate) return;
    if (!ACCEPTED.includes(candidate.type)) {
      setFile(null);
      setPreview(null);
      setStatus({ kind: "error", message: MESSAGES.unsupported_image_type });
      return;
    }
    if (candidate.size > MAX_BYTES) {
      setFile(null);
      setPreview(null);
      setStatus({ kind: "error", message: MESSAGES.image_too_large });
      return;
    }
    setFile(candidate);
    setRestored(false);
    if (status.kind === "error") setStatus({ kind: "idle" });
  }

  function remove() {
    setFile(null);
    setPreview(null);
    setStatus({ kind: "idle" });
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  async function search() {
    if (!file) return;
    setStatus({ kind: "searching" });
    const body = new FormData();
    body.set("image", file);
    try {
      const response = await fetch("/api/visual-search?limit=12", { method: "POST", body });
      const data: unknown = await response.json().catch(() => null);
      if (!response.ok) {
        const code = (data as { detail?: { code?: string } } | null)?.detail?.code ?? "unavailable";
        setStatus({ kind: "error", message: MESSAGES[code] ?? MESSAGES.visual_search_unavailable });
        return;
      }
      const result = data as VisualSearchResponse;
      setStatus({ kind: "done", result });
      setRestored(false);
      try {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(result));
      } catch {
        /* ignore */
      }
    } catch {
      setStatus({ kind: "error", message: MESSAGES.unavailable });
    }
  }

  function onDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(false);
    choose(event.dataTransfer.files?.[0]);
  }

  const searching = status.kind === "searching";
  const buttonClass =
    "inline-flex h-11 cursor-pointer items-center justify-center gap-2 rounded-lg px-5 text-sm font-semibold";

  return (
    <div className="grid gap-8 lg:grid-cols-[400px_1fr] lg:items-start">
      <section aria-labelledby="your-photo" className="rounded-2xl border border-line bg-white p-5 sm:p-6 lg:sticky lg:top-28">
        <h2 id="your-photo" className="mb-4 text-lg font-bold text-ink">
          Your photo
        </h2>

        {/* Hidden file inputs with real labels; the visible buttons open them. */}
        <label htmlFor={fileId} className="sr-only">
          Photo to search with
        </label>
        <input
          ref={fileInput}
          id={fileId}
          tabIndex={-1}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="sr-only"
          onChange={(event) => {
            choose(event.target.files?.[0]);
            event.target.value = "";
          }}
        />
        <label htmlFor={cameraId} className="sr-only">
          Take a photo to search with
        </label>
        <input
          ref={cameraInput}
          id={cameraId}
          tabIndex={-1}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          onChange={(event) => {
            choose(event.target.files?.[0]);
            event.target.value = "";
          }}
        />

        {preview && file ? (
          <div>
            {/* eslint-disable-next-line @next/next/no-img-element -- local object URL preview */}
            <img
              src={preview}
              alt={`Your photo: ${file.name}`}
              className="mx-auto max-h-80 w-full rounded-xl bg-cream object-contain"
            />
            <p className="mt-2 truncate text-xs text-muted">{file.name}</p>
            <div className="mt-4 grid gap-2">
              <button
                type="button"
                onClick={search}
                disabled={searching}
                aria-busy={searching}
                className={`${buttonClass} bg-ink text-white hover:bg-black disabled:cursor-wait disabled:opacity-70`}
              >
                {searching ? (
                  <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                ) : (
                  <ScanSearch className="size-4" aria-hidden="true" />
                )}
                {searching ? "Searching…" : "Find similar products"}
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button type="button" onClick={() => fileInput.current?.click()} disabled={searching} className={`${buttonClass} border border-line text-ink hover:bg-cream`}>
                  <RefreshCw className="size-4" aria-hidden="true" />
                  Change photo
                </button>
                <button type="button" onClick={remove} disabled={searching} className={`${buttonClass} border border-line text-ink hover:bg-cream`}>
                  <X className="size-4" aria-hidden="true" />
                  Remove
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div
            onDragOver={(event) => {
              event.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            className={`rounded-xl border-2 border-dashed p-6 text-center ${dragging ? "border-ink bg-cream" : "border-line bg-cream/40"}`}
          >
            <ImageUp className="mx-auto size-10 text-muted" aria-hidden="true" />
            <p className="mt-2 text-sm font-semibold text-ink">Drag and drop a photo here</p>
            <p className="text-xs text-muted">or</p>
            <div className="mt-3 grid gap-2">
              <button type="button" onClick={() => fileInput.current?.click()} className={`${buttonClass} bg-ink text-white hover:bg-black`}>
                <ImageUp className="size-4" aria-hidden="true" />
                Choose photo
              </button>
              <button
                type="button"
                onClick={() => cameraInput.current?.click()}
                className={`${buttonClass} border border-ink text-ink hover:bg-white`}
              >
                <Camera className="size-4" aria-hidden="true" />
                Take photo
              </button>
            </div>
            <p className="mt-3 text-xs text-muted">
              JPEG, PNG or WebP, up to 8 MB. &ldquo;Take photo&rdquo; opens the camera on phones.
            </p>
          </div>
        )}

        <p className="mt-4 text-xs text-muted">
          Your photo is only used for this search. It isn&apos;t saved, shared or used to train anything.
        </p>
      </section>

      <section aria-labelledby="results-heading" className="min-w-0">
        <div role="status" aria-live="polite" className="sr-only">
          {searching ? "Searching the catalog for similar products…" : status.kind === "done" ? `${status.result.items.length} similar products found.` : ""}
        </div>
        {status.kind === "error" && (
          <p role="alert" className="mb-4 rounded-xl border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark">
            {status.message}
          </p>
        )}
        {status.kind === "done" ? (
          <Results result={status.result} restored={restored} />
        ) : searching ? (
          <div className="flex min-h-64 flex-col items-center justify-center rounded-2xl border border-line bg-white p-8 text-center">
            <Loader2 className="size-8 animate-spin text-ink" aria-hidden="true" />
            <p className="mt-3 text-sm font-semibold text-ink">Comparing your photo with our products…</p>
          </div>
        ) : (
          <div className="rounded-2xl border border-dashed border-line bg-white p-8 text-center">
            <h2 id="results-heading" className="text-lg font-bold text-ink">
              Results appear here
            </h2>
            <p className="mx-auto mt-1 max-w-md text-sm text-muted">
              Upload a photo of shoes, clothes or a bag — from social media, a screenshot or the
              street — and we&apos;ll show the most similar items in our catalog.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function Results({ result, restored }: { result: VisualSearchResponse; restored: boolean }) {
  const { query, items } = result;
  const primary = query.type_guard_applied ? items.filter((i) => i.matches_predicted_type) : items;
  const others = query.type_guard_applied ? items.filter((i) => i.matches_predicted_type === false) : [];
  const grid = (list: typeof items) => (
    <ul className="grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-4">
      {list.map((item) => (
        <li key={item.product.id}>
          <ProductCard product={item.product} imageSizes="(min-width: 1280px) 20vw, (min-width: 768px) 30vw, 50vw" />
        </li>
      ))}
    </ul>
  );

  return (
    <div>
      <h2 id="results-heading" className="text-xl font-extrabold text-ink">
        {query.weak_matches ? "Closest products currently available" : "Best visual matches"}
      </h2>
      <p className="mt-1 text-sm text-muted">
        {restored && "Your last search. "}
        {query.weak_matches
          ? "Nothing in our catalog looks very close to your photo. These are the closest products currently available."
          : query.type_guard_applied && query.predicted_type_label
            ? `Your photo looks like ${query.predicted_type_label.toLowerCase()}, so those come first.`
            : "Similar styles from our catalog, closest first."}
      </p>
      {items.length === 0 ? (
        <p className="mt-6 text-sm text-ink">
          No products to show right now. <Link href="/shop" className="font-semibold underline">Browse the shop</Link>
        </p>
      ) : (
        <div className="mt-5 space-y-8">
          {primary.length > 0 && grid(primary)}
          {others.length > 0 && (
            <div>
              <h3 className="mb-3 text-base font-bold text-ink">Other visually similar items</h3>
              {grid(others)}
            </div>
          )}
        </div>
      )}
      <p className="mt-6 text-xs text-muted">
        Found by comparing your photo with our product photos using a pretrained image model.
        Results show similar styles, not necessarily the exact same item or brand.
      </p>
    </div>
  );
}
