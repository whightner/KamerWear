"use client";

import { useActionState, useState } from "react";
import { FormMessage, SubmitButton } from "@/components/auth/fields";
import { SelectField, TextAreaField } from "@/components/admin/fields";
import { startConversationAction, type AfterSalesFormState } from "@/lib/after-sales/actions";
import { MESSAGE_MAX_LENGTH, SUBJECT_LABELS } from "@/lib/after-sales/labels";
import type { SupportSubject } from "@/lib/after-sales/types";

export function NewConversationForm({
  orderNumber,
  returnNumber,
  defaultSubject,
}: {
  orderNumber?: string;
  returnNumber?: string;
  defaultSubject?: SupportSubject;
}) {
  const [state, action] = useActionState<AfterSalesFormState, FormData>(startConversationAction, {});
  const [subject, setSubject] = useState<string>(defaultSubject ?? "");
  const [message, setMessage] = useState("");
  return (
    <form action={action} noValidate className="space-y-4">
      {orderNumber && <input type="hidden" name="order_number" value={orderNumber} />}
      {returnNumber && <input type="hidden" name="return_number" value={returnNumber} />}
      <FormMessage error={state.error} />
      {(orderNumber || returnNumber) && (
        <p className="rounded-lg bg-cream px-3 py-2 text-sm text-ink">
          About {returnNumber ? `return ${returnNumber}` : `order ${orderNumber}`}
          {returnNumber && orderNumber ? ` (order ${orderNumber})` : ""}
        </p>
      )}
      <SelectField
        label="Subject"
        name="subject"
        value={subject}
        onChange={(event) => setSubject(event.target.value)}
        error={state.fields?.subject}
      >
        <option value="">Choose a subject</option>
        {Object.entries(SUBJECT_LABELS).map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </SelectField>
      <TextAreaField
        label="Message"
        name="message"
        rows={5}
        maxLength={MESSAGE_MAX_LENGTH}
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        hint={`Plain text, up to ${MESSAGE_MAX_LENGTH} characters. Please don't share passwords or payment details.`}
        error={state.fields?.message}
      />
      <div className="sm:w-60">
        <SubmitButton pendingLabel="Sending…">Start conversation</SubmitButton>
      </div>
    </form>
  );
}
