"use client";

import { useId, useState, type InputHTMLAttributes } from "react";
import { useFormStatus } from "react-dom";
import { Eye, EyeOff, Loader2 } from "lucide-react";

// Small form building blocks shared by the auth and account forms.

const inputClass =
  "h-11 w-full rounded-lg border bg-white px-3 text-sm text-ink outline-none placeholder:text-muted focus:border-ink focus:ring-2 focus:ring-ink/10 aria-[invalid=true]:border-deal read-only:bg-cream read-only:text-muted";

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  name: string;
  error?: string;
  hint?: string;
}

function describedBy(error?: string, errorId?: string, hint?: string, hintId?: string) {
  return [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(" ") || undefined;
}

export function TextField({ label, name, error, hint, className, ...input }: FieldProps) {
  const id = useId();
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">
        {label}
      </label>
      <input
        id={id}
        name={name}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy(error, `${id}-error`, hint, `${id}-hint`)}
        className={`${inputClass} ${error ? "border-deal" : "border-line"}`}
        {...input}
      />
      {hint && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-deal-dark">
          {error}
        </p>
      )}
    </div>
  );
}

export function PasswordField({ label, name, error, hint, className, ...input }: FieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">
        {label}
      </label>
      <div className="relative">
        <input
          id={id}
          name={name}
          type={visible ? "text" : "password"}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy(error, `${id}-error`, hint, `${id}-hint`)}
          className={`${inputClass} pr-12 ${error ? "border-deal" : "border-line"}`}
          {...input}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? `Hide ${label.toLowerCase()}` : `Show ${label.toLowerCase()}`}
          aria-pressed={visible}
          aria-controls={id}
          className="absolute right-1 top-1 flex size-9 items-center justify-center rounded-md text-muted hover:bg-cream hover:text-ink"
        >
          {visible ? (
            <EyeOff className="size-[18px]" aria-hidden="true" />
          ) : (
            <Eye className="size-[18px]" aria-hidden="true" />
          )}
        </button>
      </div>
      {hint && (
        <p id={`${id}-hint`} className="mt-1.5 text-xs text-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-deal-dark">
          {error}
        </p>
      )}
    </div>
  );
}

/** Error or success banner for a whole form. Announced by screen readers. */
export function FormMessage({ error, success }: { error?: string; success?: string }) {
  if (error) {
    return (
      <p role="alert" className="rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark">
        {error}
      </p>
    );
  }
  if (success) {
    return (
      <p role="status" className="rounded-lg border border-fit/30 bg-fit-soft px-4 py-3 text-sm font-medium text-fit-dark">
        {success}
      </p>
    );
  }
  return null;
}

export function SubmitButton({ children, pendingLabel }: { children: string; pendingLabel: string }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      aria-disabled={pending}
      className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black disabled:cursor-wait disabled:opacity-70"
    >
      {pending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {pending ? pendingLabel : children}
    </button>
  );
}
