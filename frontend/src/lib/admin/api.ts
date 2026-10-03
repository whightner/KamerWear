import "server-only";

import { call } from "@/lib/api/server";
import type {
  AdminCategory,
  AdminOrder,
  AdminOrderSummary,
  AdminProduct,
  AdminProductListItem,
  InventoryList,
  InventoryRow,
  Overview,
  Paged,
} from "./types";

// Server-side calls to the admin API. FastAPI checks that the token belongs to
// an ADMIN on every call; these helpers don't decide anything themselves.

type Query = Record<string, string | number | boolean | undefined | null>;

function withQuery(path: string, query: Query = {}): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "" && value !== false) {
      params.set(key, String(value));
    }
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

const get = <T>(token: string, path: string, query?: Query) =>
  call<T>(withQuery(path, query), { accessToken: token });
const send = <T>(token: string, method: string, path: string, body?: unknown) =>
  call<T>(path, { method, body, accessToken: token });

export const adminApi = {
  overview: (t: string) => get<Overview>(t, "/admin/overview"),

  categories: (t: string) => get<AdminCategory[]>(t, "/admin/categories"),
  createCategory: (t: string, body: unknown) =>
    send<AdminCategory>(t, "POST", "/admin/categories", body),
  updateCategory: (t: string, id: number, body: unknown) =>
    send<AdminCategory>(t, "PATCH", `/admin/categories/${id}`, body),

  products: (t: string, query: Query) =>
    get<Paged<AdminProductListItem>>(t, "/admin/products", query),
  product: (t: string, id: number) => get<AdminProduct>(t, `/admin/products/${id}`),
  createProduct: (t: string, body: unknown) =>
    send<AdminProduct>(t, "POST", "/admin/products", body),
  updateProduct: (t: string, id: number, body: unknown) =>
    send<AdminProduct>(t, "PATCH", `/admin/products/${id}`, body),
  createVariant: (t: string, productId: number, body: unknown) =>
    send<AdminProduct>(t, "POST", `/admin/products/${productId}/variants`, body),
  updateVariant: (t: string, id: number, body: unknown) =>
    send<AdminProduct>(t, "PATCH", `/admin/variants/${id}`, body),
  createImage: (t: string, productId: number, body: unknown) =>
    send<AdminProduct>(t, "POST", `/admin/products/${productId}/images`, body),
  updateImage: (t: string, id: number, body: unknown) =>
    send<AdminProduct>(t, "PATCH", `/admin/images/${id}`, body),
  deleteImage: (t: string, id: number) =>
    send<AdminProduct>(t, "DELETE", `/admin/images/${id}`),

  inventory: (t: string, query: Query) => get<InventoryList>(t, "/admin/inventory", query),
  setOnHand: (t: string, variantId: number, onHand: number) =>
    send<InventoryRow>(t, "PATCH", `/admin/inventory/${variantId}`, { on_hand: onHand }),

  orders: (t: string, query: Query) =>
    get<Paged<AdminOrderSummary>>(t, "/admin/orders", query),
  order: (t: string, number: string) =>
    get<AdminOrder>(t, `/admin/orders/${encodeURIComponent(number)}`),
  changeStatus: (t: string, number: string, body: unknown) =>
    send<AdminOrder>(t, "POST", `/admin/orders/${encodeURIComponent(number)}/status`, body),
  changePayment: (t: string, number: string, body: unknown) =>
    send<AdminOrder>(
      t,
      "POST",
      `/admin/orders/${encodeURIComponent(number)}/payment-status`,
      body,
    ),
};
