import "server-only";

import { call } from "@/lib/api/server";
import type {
  Address,
  AddressInput,
  Cart,
  CartAdjustment,
  OrderDetail,
  OrderList,
  PaymentMethod,
  Quote,
} from "./types";

// Server-side calls to the cart, address, checkout and order endpoints. The
// customer is always identified by the access token, never by an id we send.

export const commerceApi = {
  cart: (token: string) => call<Cart>("/cart", { accessToken: token }),
  addToCart: (token: string, variantId: number, quantity: number) =>
    call<Cart>("/cart/items", {
      method: "POST",
      body: { variant_id: variantId, quantity },
      accessToken: token,
    }),
  updateCartItem: (token: string, itemId: number, quantity: number) =>
    call<Cart>(`/cart/items/${itemId}`, {
      method: "PATCH",
      body: { quantity },
      accessToken: token,
    }),
  removeCartItem: (token: string, itemId: number) =>
    call<Cart>(`/cart/items/${itemId}`, { method: "DELETE", accessToken: token }),
  mergeCart: (token: string, items: { variant_id: number; quantity: number }[]) =>
    call<{ cart: Cart; adjustments: CartAdjustment[] }>("/cart/merge", {
      method: "POST",
      body: { items },
      accessToken: token,
    }),

  addresses: (token: string) => call<Address[]>("/addresses", { accessToken: token }),
  createAddress: (token: string, data: AddressInput) =>
    call<Address>("/addresses", { method: "POST", body: data, accessToken: token }),
  updateAddress: (token: string, id: number, data: Partial<AddressInput>) =>
    call<Address>(`/addresses/${id}`, { method: "PATCH", body: data, accessToken: token }),
  deleteAddress: (token: string, id: number) =>
    call<void>(`/addresses/${id}`, { method: "DELETE", accessToken: token }),

  quote: (token: string, addressId: number | null, paymentMethod: PaymentMethod | null) =>
    call<Quote>("/checkout/quote", {
      method: "POST",
      body: { address_id: addressId, payment_method: paymentMethod },
      accessToken: token,
    }),
  placeOrder: (
    token: string,
    data: { address_id: number; payment_method: PaymentMethod; expected_total: number },
    idempotencyKey: string,
  ) =>
    call<OrderDetail>("/orders", {
      method: "POST",
      body: data,
      accessToken: token,
      headers: { "Idempotency-Key": idempotencyKey },
    }),
  orders: (token: string) => call<OrderList>("/orders?limit=50", { accessToken: token }),
  order: (token: string, orderNumber: string) =>
    call<OrderDetail>(`/orders/${encodeURIComponent(orderNumber)}`, { accessToken: token }),
};
