import { ChevronDown, MapPin } from "lucide-react";

/** Demo destination. The city picker comes with the address task. */
export function DeliveryCityButton({ className = "" }: { className?: string }) {
  return (
    <button
      type="button"
      title="Choose delivery city (coming soon)"
      aria-label="Delivery city: Douala. Choose delivery city, coming soon"
      className={`items-center gap-1.5 rounded-md border border-line px-2.5 py-1.5 text-xs text-muted hover:border-ink/40 hover:bg-cream ${className}`}
    >
      <MapPin className="size-3.5 text-deal" aria-hidden="true" />
      Deliver to
      <span className="font-semibold text-ink">Douala</span>
      <ChevronDown className="size-3.5 text-ink" aria-hidden="true" />
    </button>
  );
}
