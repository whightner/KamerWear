"use client";

import { useActionState } from "react";
import Link from "next/link";
import { loginAction, type FormState } from "@/lib/auth/actions";
import { FormMessage, PasswordField, SubmitButton, TextField } from "./fields";

export function LoginForm({ next, notice }: { next: string; notice?: string }) {
  const [state, formAction] = useActionState<FormState, FormData>(loginAction, {});
  const registerHref = next === "/account" ? "/register" : `/register?next=${encodeURIComponent(next)}`;

  return (
    <form action={formAction} noValidate className="space-y-5">
      <input type="hidden" name="next" value={next} />
      {state.error ? (
        <FormMessage error={state.error} />
      ) : (
        notice && (
          <p role="status" className="rounded-lg border border-gold/40 bg-gold-soft px-4 py-3 text-sm font-medium text-ink">
            {notice}
          </p>
        )
      )}
      <TextField
        label="Email"
        name="email"
        type="email"
        autoComplete="email"
        inputMode="email"
        required
        defaultValue={state.values?.email}
        error={state.fields?.email}
      />
      <PasswordField
        label="Password"
        name="password"
        autoComplete="current-password"
        required
        error={state.fields?.password}
      />
      <SubmitButton pendingLabel="Logging in…">Log in</SubmitButton>
      <p className="text-center text-sm text-muted">
        New to KamerWear?{" "}
        <Link href={registerHref} className="font-semibold text-ink underline underline-offset-2">
          Create an account
        </Link>
      </p>
    </form>
  );
}
