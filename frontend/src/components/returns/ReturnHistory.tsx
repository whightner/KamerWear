import { RETURN_STATUS_LABELS } from "@/lib/after-sales/labels";
import type { ReturnStatus } from "@/lib/after-sales/types";
import { formatDateTime } from "@/lib/commerce/labels";

interface Event {
  status: ReturnStatus;
  note: string | null;
  created_at: string;
  internal_note?: string | null;
  changed_by?: string | null;
}

/** Status history, oldest first. Internal notes only appear when passed (admin). */
export function ReturnHistory({ events, label = "Return history" }: { events: Event[]; label?: string }) {
  return (
    <ol aria-label={label} className="space-y-4 border-l-2 border-line pl-4">
      {events.map((event, index) => (
        <li key={`${event.status}-${index}`} className="relative">
          <span
            aria-hidden="true"
            className="absolute -left-[23px] top-1 size-3 rounded-full border-2 border-white bg-fit"
          />
          <p className="text-sm font-semibold text-ink">{RETURN_STATUS_LABELS[event.status]}</p>
          <p className="text-xs text-muted">
            <time dateTime={event.created_at}>{formatDateTime(event.created_at)}</time>
            {event.changed_by && <> · {event.changed_by}</>}
          </p>
          {event.note && <p className="mt-1 whitespace-pre-wrap text-sm text-ink">{event.note}</p>}
          {event.internal_note && (
            <p className="mt-1 whitespace-pre-wrap rounded bg-gold-soft px-2 py-1 text-xs text-ink">
              <span className="font-semibold">Internal: </span>
              {event.internal_note}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
