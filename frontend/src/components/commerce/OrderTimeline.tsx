import { Check, Circle, XCircle } from "lucide-react";
import { formatDateTime } from "@/lib/commerce/labels";
import type { OrderDetail } from "@/lib/commerce/types";

/** Status tracking (not GPS): the delivery steps marked done, current or upcoming. */
export function OrderTimeline({ order }: { order: OrderDetail }) {
  return (
    <div>
      {order.is_cancelled && (
        <p className="mb-4 flex items-center gap-2 rounded-lg bg-deal-soft px-4 py-3 text-sm font-semibold text-deal-dark">
          <XCircle className="size-4" aria-hidden="true" />
          This order was cancelled.
        </p>
      )}
      <ol className="relative">
        {order.timeline.map((step, index) => {
          const last = index === order.timeline.length - 1;
          const done = step.state === "done";
          const current = step.state === "current";
          return (
            <li key={step.status} className="relative flex gap-4 pb-6 last:pb-0">
              {!last && (
                <span
                  aria-hidden="true"
                  className={`absolute left-[13px] top-7 h-[calc(100%-28px)] w-0.5 ${done ? "bg-fit" : "bg-line"}`}
                />
              )}
              <span
                aria-hidden="true"
                className={`relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full border-2 ${
                  done
                    ? "border-fit bg-fit text-white"
                    : current
                      ? "border-ink bg-white text-ink"
                      : "border-line bg-white text-line"
                }`}
              >
                {done ? (
                  <Check className="size-4" />
                ) : (
                  <Circle className={`size-2.5 ${current ? "fill-ink" : "fill-line"}`} />
                )}
              </span>
              <div className="pt-0.5">
                <p className={`text-sm font-semibold ${step.state === "upcoming" ? "text-muted" : "text-ink"}`}>
                  {step.label}
                  <span className="sr-only">
                    {done ? " — completed" : current ? " — current step" : " — not yet"}
                  </span>
                </p>
                {step.reached_at && (
                  <p className="text-xs text-muted">{formatDateTime(step.reached_at)}</p>
                )}
                {current && <p className="text-xs font-medium text-ink">Current status</p>}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
