/** Shown when an admin API call fails (e.g. the API is unreachable). */
export function AdminError({ what }: { what: string }) {
  return (
    <p role="alert" className="rounded-xl border border-line bg-white px-6 py-10 text-center text-sm text-ink">
      We couldn&apos;t load {what} right now. Please try again in a moment.
    </p>
  );
}
