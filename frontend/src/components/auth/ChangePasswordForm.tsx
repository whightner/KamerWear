"use client";

import { useActionState } from "react";
import { changePasswordAction, type FormState } from "@/lib/auth/actions";
import { FormMessage, PasswordField, SubmitButton } from "./fields";

export function ChangePasswordForm() {
  const [state, formAction] = useActionState<FormState, FormData>(changePasswordAction, {});

  return (
    <form action={formAction} noValidate className="space-y-5">
      <FormMessage error={state.error} success={state.success} />
      <PasswordField
        label="Current password"
        name="current_password"
        autoComplete="current-password"
        required
        error={state.fields?.current_password}
      />
      <PasswordField
        label="New password"
        name="new_password"
        autoComplete="new-password"
        required
        minLength={10}
        maxLength={128}
        hint="At least 10 characters, different from your current password."
        error={state.fields?.new_password}
      />
      <PasswordField
        label="Confirm new password"
        name="confirm_password"
        autoComplete="new-password"
        required
        maxLength={128}
        error={state.fields?.confirm_password}
      />
      <div className="sm:w-48">
        <SubmitButton pendingLabel="Updating…">Update password</SubmitButton>
      </div>
    </form>
  );
}
