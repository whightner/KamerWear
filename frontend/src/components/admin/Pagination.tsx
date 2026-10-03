import Link from "next/link";

/** Previous/next links that keep the current filters. */
export function Pagination({
  basePath,
  params,
  total,
  limit,
  offset,
}: {
  basePath: string;
  params: Record<string, string | undefined>;
  total: number;
  limit: number;
  offset: number;
}) {
  if (total <= limit) return null;
  const href = (nextOffset: number) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) if (value) query.set(key, value);
    if (nextOffset > 0) query.set("offset", String(nextOffset));
    const qs = query.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  };
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);
  const linkClass = "rounded-lg border border-line bg-white px-3 py-1.5 font-semibold text-ink hover:bg-cream";
  return (
    <nav aria-label="Pagination" className="mt-4 flex items-center justify-between text-sm">
      <p className="text-muted">
        Page {page} of {pages} · {total} total
      </p>
      <div className="flex gap-2">
        {offset > 0 && (
          <Link href={href(Math.max(0, offset - limit))} className={linkClass}>
            Previous
          </Link>
        )}
        {offset + limit < total && (
          <Link href={href(offset + limit)} className={linkClass}>
            Next
          </Link>
        )}
      </div>
    </nav>
  );
}
