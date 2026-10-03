"use client";

import { useActionState } from "react";
import Link from "next/link";
import { registerAction, type FormState } from "@/lib/auth/actions";
import { FormMessage, PasswordField, SubmitButton, TextField } from "./fields";

export function RegisterForm({ next }: { next: string }) {
  const [state, formAction] = useActionState<FormState, FormData>(registerAction, {});
  const loginHref = next === "/account" ? "/login" : `/login?next=${encodeURIComponent(next)}`;

  return (
    <form action={formAction} noValidate className="space-y-5">
      <input type="hidden" name="next" value={next} />
      <FormMessage error={state.error} />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="First name"
          name="first_name"
          autoComplete="given-name"
          required
          maxLength={80}
          defaultValue={state.values?.first_name}
          error={state.fields?.first_name}
        />
        <TextField
          label="Last name"
          name="last_name"
          autoComplete="family-name"
          required
          maxLength={80}
          defaultValue={state.values?.last_name}
          error={state.fields?.last_name}
        />
      </div>
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
      <TextField
        label="Phone (optional)"
        name="phone"
        type="tel"
        autoComplete="tel"
        placeholder="+237 6XX XX XX XX"
        maxLength={30}
        defaultValue={state.values?.phone}
        error={state.fields?.phone}
      />
      <PasswordField
        label="Password"
        name="password"
        autoComplete="new-password"
        required
        minLength={10}
        maxLength={128}
        hint="At least 10 characters. A short phrase you can remember works well."
        error={state.fields?.password}
      />
      <PasswordField
        label="Confirm password"
        name="confirm_password"
        autoComplete="new-password"
        required
        maxLength={128}
        error={state.fields?.confirm_password}
      />
      <SubmitButton pendingLabel="Creating account…">Create account</SubmitButton>
      <p className="text-center text-sm text-muted">
        Already have an account?{" "}
        <Link href={loginHref} className="font-semibold text-ink underline underline-offset-2">
          Log in
        </Link>
      </p>
    </form>
  );
}
