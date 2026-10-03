"use client";

import Image from "next/image";
import type { ProductImage } from "@/types/catalog";

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

  return (
    <div className="flex flex-col-reverse gap-3 sm:flex-row">
      {images.length > 1 && (
        <ul className="flex gap-2 sm:flex-col" aria-label="Product photos">
          {images.map((image, index) => (
            <li key={image.src}>
              <button
                type="button"
                onClick={() => onSelect(index)}
                aria-label={`Show ${image.alt}`}
                aria-pressed={index === selected}
                className={`relative block aspect-[4/5] w-16 overflow-hidden rounded-lg border-2 bg-[#f2f2f2] lg:w-20 ${
                  index === selected
                    ? "border-ink"
                    : "border-transparent hover:border-line"
                }`}
              >
                <Image
                  src={image.src}
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
          key={current.src}
          src={current.src}
          alt={current.alt}
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
