export function Logo({ inverted = false }: { inverted?: boolean }) {
  return (
    <a
      href="#top"
      aria-label="KamerWear home"
      className={`text-2xl font-black uppercase tracking-tight ${inverted ? "text-white" : "text-ink"}`}
    >
      Kamer<span className="text-deal">Wear</span>
    </a>
  );
}
