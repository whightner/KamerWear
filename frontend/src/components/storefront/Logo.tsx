import Link from "next/link";

export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <Link
      href="/"
      aria-label="KamerWear home"
      className={`text-2xl font-black uppercase tracking-tight ${inverted ? "text-white" : "text-ink"}`}
    >
      Kamer<span className="text-deal">Wear</span>
    </Link>
  );
}
