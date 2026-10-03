"use client";

import { useActionState } from "react";
import { updateProfileAction, type FormState } from "@/lib/auth/actions";
import { FormMessage, SubmitButton, TextField } from "./fields";

interface Props {
  email: string;
  firstName: string;
  lastName: string;
  phone: string;
}

export function ProfileForm({ email, firstName, lastName, phone }: Props) {
  const [state, formAction] = useActionState<FormState, FormData>(updateProfileAction, {
    values: { first_name: firstName, last_name: lastName, phone },
  });
  const values = state.values ?? {};

  return (
    <form action={formAction} noValidate className="space-y-5">
      <FormMessage error={state.error} success={state.success} />
      <div className="grid gap-5 sm:grid-cols-2">
        <TextField
          label="First name"
          name="first_name"
          autoComplete="given-name"
          required
          maxLength={80}
          defaultValue={values.first_name}
          error={state.fields?.first_name}
        />
        <TextField
          label="Last name"
          name="last_name"
          autoComplete="family-name"
          required
          maxLength={80}
          defaultValue={values.last_name}
          error={state.fields?.last_name}
        />
      </div>
      <TextField
        label="Email"
        name="email_display"
        type="email"
        value={email}
        readOnly
        hint="Your email is used to log in and can't be changed here."
      />
      <TextField
        label="Phone (optional)"
        name="phone"
        type="tel"
        autoComplete="tel"
        placeholder="+237 6XX XX XX XX"
        maxLength={30}
        defaultValue={values.phone}
        error={state.fields?.phone}
      />
      <div className="sm:w-48">
        <SubmitButton pendingLabel="Saving…">Save changes</SubmitButton>
      </div>
    </form>
  );
}
