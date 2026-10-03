"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { MapPin, Plus } from "lucide-react";
import { deleteAddressAction, setDefaultAddressAction } from "@/lib/commerce/actions";
import type { Address } from "@/lib/commerce/types";
import { AddressDetails } from "./AddressDetails";
import { AddressForm } from "./AddressForm";

/** The account page list: add, edit, set default and delete addresses. */
export function AddressBook({
  addresses,
  defaults,
}: {
  addresses: Address[];
  defaults: { recipient_name: string; phone: string };
}) {
  const router = useRouter();
  const [editing, setEditing] = useState<number | "new" | null>(
    addresses.length === 0 ? "new" : null,
  );
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);
  const [message, setMessage] = useState<{ error?: string; success?: string }>({});
  const [pending, startTransition] = useTransition();

  function run(action: () => Promise<{ ok: boolean; message?: string; code?: string }>, done: string) {
    setMessage({});
    startTransition(async () => {
      const result = await action();
      if (result.ok) {
        setMessage({ success: done });
        setConfirmDelete(null);
      } else if (result.code === "session_expired") {
        router.push("/login?next=%2Faccount%2Faddresses&reason=expired");
      } else {
        setMessage({ error: result.message });
      }
    });
  }

  return (
    <div className="space-y-4">
      <div aria-live="polite">
        {message.error && (
          <p role="alert" className="rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark">
            {message.error}
          </p>
        )}
        {message.success && (
          <p className="rounded-lg border border-fit/30 bg-fit-soft px-4 py-3 text-sm font-medium text-fit-dark">
            {message.success}
          </p>
        )}
      </div>

      {addresses.length > 0 && (
        <ul className="grid gap-4 md:grid-cols-2">
          {addresses.map((address) => (
            <li key={address.id} className="rounded-xl border border-line bg-white p-5">
              {editing === address.id ? (
                <>
                  <h2 className="mb-4 font-bold text-ink">Edit {address.label}</h2>
                  <AddressForm
                    address={address}
                    onSaved={() => {
                      setEditing(null);
                      setMessage({ success: "Address updated." });
                    }}
                    onCancel={() => setEditing(null)}
                  />
                </>
              ) : (
                <>
                  <div className="mb-2 flex items-center gap-2">
                    <MapPin className="size-4 text-ink" aria-hidden="true" />
                    <h2 className="font-bold text-ink">{address.label}</h2>
                    {address.is_default && (
                      <span className="rounded-full bg-fit-soft px-2 py-0.5 text-[11px] font-semibold text-fit-dark">
                        Default
                      </span>
                    )}
                  </div>
                  <AddressDetails address={{ ...address, landmark: address.street_or_landmark }} />
                  <div className="mt-4 flex flex-wrap gap-2 text-sm">
                    <button
                      type="button"
                      onClick={() => {
                        setEditing(address.id);
                        setMessage({});
                      }}
                      className="h-9 rounded-lg border border-line px-3 font-semibold text-ink hover:bg-cream"
                    >
                      Edit
                    </button>
                    {!address.is_default && (
                      <button
                        type="button"
                        disabled={pending}
                        onClick={() =>
                          run(() => setDefaultAddressAction(address.id), `${address.label} is now your default address.`)
                        }
                        className="h-9 rounded-lg border border-line px-3 font-semibold text-ink hover:bg-cream"
                      >
                        Set as default
                      </button>
                    )}
                    {confirmDelete === address.id ? (
                      <>
                        <button
                          type="button"
                          disabled={pending}
                          onClick={() => run(() => deleteAddressAction(address.id), "Address deleted.")}
                          className="h-9 rounded-lg bg-deal-dark px-3 font-semibold text-white"
                        >
                          Confirm delete
                        </button>
                        <button
                          type="button"
                          onClick={() => setConfirmDelete(null)}
                          className="h-9 rounded-lg px-3 font-semibold text-muted hover:text-ink"
                        >
                          Keep
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmDelete(address.id)}
                        aria-label={`Delete ${address.label}`}
                        className="h-9 rounded-lg px-3 font-semibold text-deal-dark hover:bg-deal-soft"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </>
              )}
            </li>
          ))}
        </ul>
      )}

      {editing === "new" ? (
        <section aria-labelledby="new-address" className="rounded-xl border border-line bg-white p-5 sm:p-6">
          <h2 id="new-address" className="mb-4 text-lg font-bold text-ink">
            Add a delivery address
          </h2>
          <AddressForm
            defaults={defaults}
            onSaved={() => {
              setEditing(null);
              setMessage({ success: "Address saved." });
            }}
            onCancel={addresses.length ? () => setEditing(null) : undefined}
          />
        </section>
      ) : (
        <button
          type="button"
          onClick={() => {
            setEditing("new");
            setMessage({});
          }}
          className="flex h-11 items-center gap-2 rounded-lg bg-ink px-5 text-sm font-semibold text-white hover:bg-black"
        >
          <Plus className="size-4" aria-hidden="true" />
          Add an address
        </button>
      )}
    </div>
  );
}
