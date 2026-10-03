"use client";

import { useActionState, useState, useTransition } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFormStatus } from "react-dom";
import { Banknote, CreditCard, Loader2, Plus, Smartphone, type LucideIcon } from "lucide-react";
import {
  placeOrderAction,
  quoteAction,
  type PlaceOrderState,
} from "@/lib/commerce/actions";
import { formatXaf } from "@/lib/format";
import type { Address, PaymentMethod, Quote } from "@/lib/commerce/types";
import { AddressDetails } from "./AddressDetails";
import { AddressForm } from "./AddressForm";
import { OrderTotals } from "./OrderTotals";

const PAYMENT_OPTIONS: {
  value: PaymentMethod;
  label: string;
  description: string;
  icon: LucideIcon;
}[] = [
  {
    value: "mobile_money",
    label: "Mobile Money",
    description: "MTN MoMo or Orange Money (demo)",
    icon: Smartphone,
  },
  { value: "card", label: "Card", description: "Visa or Mastercard (demo)", icon: CreditCard },
  {
    value: "cash_on_delivery",
    label: "Cash on Delivery",
    description: "Pay the courier when your order arrives",
    icon: Banknote,
  },
];

function StepHeading({ step, children }: { step: number; children: string }) {
  return (
    <h2 className="mb-4 flex items-center gap-3 text-lg font-bold text-ink">
      <span className="flex size-7 items-center justify-center rounded-full bg-ink text-sm text-white">
        {step}
      </span>
      {children}
    </h2>
  );
}

interface Props {
  addresses: Address[];
  initialQuote: Quote;
  idempotencyKey: string;
  addressDefaults: { recipient_name: string; phone: string };
}

export function CheckoutView({ addresses, initialQuote, idempotencyKey, addressDefaults }: Props) {
  const router = useRouter();
  const [addressId, setAddressId] = useState<number | null>(initialQuote.address?.id ?? null);
  const [method, setMethod] = useState<PaymentMethod | null>(initialQuote.payment_method);
  const [quote, setQuote] = useState(initialQuote);
  const [quoteError, setQuoteError] = useState("");
  const [adding, setAdding] = useState(addresses.length === 0);
  const [quoting, startQuote] = useTransition();
  const [orderState, placeOrder] = useActionState<PlaceOrderState, FormData>(placeOrderAction, {});

  // A failed order attempt comes back with a fresh server quote: show it.
  const [seenOrderState, setSeenOrderState] = useState(orderState);
  if (seenOrderState !== orderState) {
    setSeenOrderState(orderState);
    if (orderState.quote) setQuote(orderState.quote);
  }

  function requote(nextAddress: number | null, nextMethod: PaymentMethod | null) {
    setQuoteError("");
    startQuote(async () => {
      const result = await quoteAction(nextAddress, nextMethod);
      if (result.ok) {
        setQuote(result.data);
      } else if (result.code === "session_expired") {
        router.push("/login?next=%2Fcheckout&reason=expired");
      } else if (result.code === "address_not_found") {
        setAddressId(null);
        setQuoteError("This address is no longer available. Please choose another one.");
      } else {
        setQuoteError(result.message);
      }
    });
  }

  function chooseAddress(id: number) {
    setAddressId(id);
    requote(id, method);
  }

  function chooseMethod(value: PaymentMethod) {
    setMethod(value);
    requote(addressId, value);
  }

  const canPlace = quote.can_place_order && !quoting && addressId !== null && method !== null;

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_380px] lg:items-start">
      <div className="space-y-6">
        <section aria-labelledby="step-address" className="rounded-xl border border-line bg-white p-5 sm:p-6">
          <div id="step-address">
            <StepHeading step={1}>Delivery address</StepHeading>
          </div>
          {addresses.length > 0 && (
            <fieldset>
              <legend className="sr-only">Choose a delivery address</legend>
              <div className="grid gap-3 md:grid-cols-2">
                {addresses.map((address) => {
                  const selected = address.id === addressId;
                  return (
                    <label
                      key={address.id}
                      className={`relative flex cursor-pointer gap-3 rounded-lg border-2 p-4 ${
                        selected ? "border-ink bg-cream/60" : "border-line hover:border-muted"
                      }`}
                    >
                      <input
                        type="radio"
                        name="address_choice"
                        value={address.id}
                        checked={selected}
                        onChange={() => chooseAddress(address.id)}
                        className="mt-1 size-4 accent-ink"
                      />
                      <span className="min-w-0">
                        <span className="mb-1 flex items-center gap-2">
                          <span className="font-bold text-ink">{address.label}</span>
                          {address.is_default && (
                            <span className="rounded-full bg-fit-soft px-2 py-0.5 text-[11px] font-semibold text-fit-dark">
                              Default
                            </span>
                          )}
                        </span>
                        <AddressDetails address={{ ...address, landmark: address.street_or_landmark }} />
                      </span>
                    </label>
                  );
                })}
              </div>
            </fieldset>
          )}
          {quoteError && (
            <p role="alert" className="mt-3 text-sm font-medium text-deal-dark">
              {quoteError}
            </p>
          )}
          {adding ? (
            <div className={addresses.length ? "mt-5 border-t border-line pt-5" : ""}>
              <h3 className="mb-4 font-bold text-ink">New address</h3>
              <AddressForm
                defaults={addressDefaults}
                submitLabel="Save and use"
                onSaved={(address) => {
                  setAdding(false);
                  chooseAddress(address.id);
                }}
                onCancel={addresses.length ? () => setAdding(false) : undefined}
              />
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setAdding(true)}
              className="mt-4 flex items-center gap-2 text-sm font-semibold text-ink underline underline-offset-2"
            >
              <Plus className="size-4" aria-hidden="true" />
              Add a new address
            </button>
          )}
        </section>

        <section aria-labelledby="step-payment" className="rounded-xl border border-line bg-white p-5 sm:p-6">
          <div id="step-payment">
            <StepHeading step={2}>Payment method</StepHeading>
          </div>
          <fieldset>
            <legend className="sr-only">Choose a payment method</legend>
            <div className="grid gap-3 sm:grid-cols-3">
              {PAYMENT_OPTIONS.map(({ value, label, description, icon: Icon }) => {
                const selected = value === method;
                return (
                  <label
                    key={value}
                    className={`flex cursor-pointer flex-col gap-1 rounded-lg border-2 p-4 ${
                      selected ? "border-ink bg-cream/60" : "border-line hover:border-muted"
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="payment_choice"
                        value={value}
                        checked={selected}
                        onChange={() => chooseMethod(value)}
                        className="size-4 accent-ink"
                      />
                      <Icon className="size-4 text-ink" aria-hidden="true" />
                      <span className="font-bold text-ink">{label}</span>
                    </span>
                    <span className="text-xs text-muted">{description}</span>
                  </label>
                );
              })}
            </div>
          </fieldset>
          {quote.payment_note && (
            <p
              role="note"
              className={`mt-4 rounded-lg px-4 py-3 text-sm ${
                method === "cash_on_delivery"
                  ? "bg-cream text-ink"
                  : "border border-gold/40 bg-gold-soft font-medium text-ink"
              }`}
            >
              {quote.payment_note}
            </p>
          )}
        </section>
      </div>

      <section
        aria-labelledby="step-review"
        aria-busy={quoting}
        className="rounded-xl border border-line bg-white p-5 sm:p-6 lg:sticky lg:top-28"
      >
        <div id="step-review">
          <StepHeading step={3}>Review your order</StepHeading>
        </div>
        <ul className="divide-y divide-line">
          {quote.items.map((line) => (
            <li key={line.cart_item_id} className="flex gap-3 py-3">
              <div className="relative aspect-[4/5] w-14 shrink-0 overflow-hidden rounded-md bg-[#f2f2f2]">
                {line.product.image && (
                  <Image
                    src={line.product.image.image_path}
                    alt={line.product.image.alt_text}
                    fill
                    sizes="56px"
                    className="object-cover"
                  />
                )}
              </div>
              <div className="min-w-0 flex-1 text-sm">
                <p className="truncate font-semibold text-ink">{line.product.name}</p>
                <p className="text-muted">
                  {line.variant.color_name}
                  {line.variant.size &&
                    ` · ${line.product.category_slug === "shoes" ? "EU " : ""}${line.variant.size}`}
                  {` · × ${line.quantity}`}
                </p>
                {line.issue && <p className="text-xs font-medium text-deal-dark">{line.issue}</p>}
              </div>
              <p className="text-sm font-semibold text-ink">{formatXaf(line.line_total)}</p>
            </li>
          ))}
        </ul>
        <div className="mt-3 border-t border-line pt-4">
          <OrderTotals
            subtotal={quote.subtotal}
            deliveryFee={quote.delivery_fee}
            discountTotal={quote.discount_total}
            total={quote.total}
          />
          <p className="mt-2 text-xs text-muted">
            Calculated by KamerWear from current prices, stock and your delivery city.
          </p>
        </div>

        {orderState.error && (
          <p
            role="alert"
            className="mt-4 rounded-lg border border-deal/30 bg-deal-soft px-4 py-3 text-sm font-medium text-deal-dark"
          >
            {orderState.error}
          </p>
        )}
        {!orderState.error && quote.issues.length > 0 && (
          <ul className="mt-4 space-y-1 text-sm text-deal-dark">
            {quote.issues.map((issue) => (
              <li key={issue}>{issue}</li>
            ))}
          </ul>
        )}
        {quote.items.some((line) => line.issue) && (
          <Link href="/cart" className="mt-2 inline-block text-sm font-semibold text-ink underline">
            Update your cart
          </Link>
        )}

        <form action={placeOrder} className="mt-5">
          <input type="hidden" name="address_id" value={addressId ?? ""} />
          <input type="hidden" name="payment_method" value={method ?? ""} />
          <input type="hidden" name="expected_total" value={quote.total} />
          <input type="hidden" name="idempotency_key" value={idempotencyKey} />
          <PlaceOrderButton disabled={!canPlace} total={quote.total} />
        </form>
      </section>
    </div>
  );
}

/** Disabled while the order is being placed, so it can't be sent twice by
 * accident. The server's idempotency key protects against repeats anyway. */
function PlaceOrderButton({ disabled, total }: { disabled: boolean; total: number }) {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={disabled || pending}
      className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-ink px-6 text-sm font-semibold text-white hover:bg-black disabled:cursor-not-allowed disabled:bg-muted/60"
    >
      {pending && <Loader2 className="size-4 animate-spin" aria-hidden="true" />}
      {pending ? "Placing your order…" : `Place order · ${formatXaf(total)}`}
    </button>
  );
}
