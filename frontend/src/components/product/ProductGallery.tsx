"use client";

import Image from "next/image";
import type { ProductImage } from "@/lib/api/types";

interface ProductGalleryProps {
  images: ProductImage[];
  selected: number;
  onSelect: (index: number) => void;
}

// Shows only real photos of the selected colour. With one photo there are no
// thumbnails, rather than repeating the same image.
export function ProductGallery({
  images,
  selected,
  onSelect,
}: ProductGalleryProps) {
  const current = images[selected] ?? images[0];
  if (!current) {
    return <div className="aspect-[4/5] w-full rounded-xl bg-[#f2f2f2]" />;
  }

  return (
    <div className="flex flex-col-reverse gap-3 sm:flex-row">
      {images.length > 1 && (
        <ul className="flex gap-2 sm:flex-col" aria-label="Product photos">
          {images.map((image, index) => (
            <li key={image.image_path}>
              <button
                type="button"
                onClick={() => onSelect(index)}
                aria-label={`Show ${image.alt_text}`}
                aria-pressed={index === selected}
                className={`relative block aspect-[4/5] w-16 overflow-hidden rounded-lg border-2 bg-[#f2f2f2] lg:w-20 ${
                  index === selected
                    ? "border-ink"
                    : "border-transparent hover:border-line"
                }`}
              >
                <Image
                  src={image.image_path}
                  alt=""
                  fill
                  sizes="80px"
                  className="object-cover"
                />
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="relative aspect-[4/5] w-full overflow-hidden rounded-xl bg-[#f2f2f2]">
        <Image
          key={current.image_path}
          src={current.image_path}
          alt={current.alt_text}
          fill
          loading="eager"
          fetchPriority="high"
          sizes="(min-width: 1024px) 560px, 100vw"
          className="object-cover"
        />
      </div>
    </div>
  );
}
