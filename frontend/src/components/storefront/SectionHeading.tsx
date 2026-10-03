import type { ReactNode } from "react";
import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface SectionHeadingProps {
  id: string;
  title: ReactNode;
  subtitle?: string;
  action?: { label: string; href: string };
  children?: ReactNode;
}

export function SectionHeading({
  id,
  title,
  subtitle,
  action,
  children,
}: SectionHeadingProps) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
        <div>
          <h2
            id={id}
            className="text-2xl font-extrabold tracking-tight text-ink"
          >
            {title}
          </h2>
          {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
        </div>
        {children}
      </div>
      {action && (
        <Link
          href={action.href}
          className="flex items-center gap-0.5 text-sm font-semibold text-ink hover:text-deal"
        >
          {action.label}
          <ChevronRight className="size-4" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
