import "server-only";

import { call } from "@/lib/api/server";
import type {
  AdminConversationDetail,
  AdminConversationSummary,
  AdminReturnDetail,
  AdminReturnSummary,
  AttentionCounts,
  ConversationDetail,
  ConversationSummary,
  Paged,
  ReturnDetail,
  ReturnEligibility,
  ReturnSummary,
} from "./types";

// Server-side calls for returns and support. FastAPI enforces ownership and
// the ADMIN role; these helpers only forward the access token.

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
const post = <T>(token: string, path: string, body: unknown = {}) =>
  call<T>(path, { method: "POST", body, accessToken: token });
const enc = encodeURIComponent;

export const returnsApi = {
  eligibility: (t: string, order: string) =>
    get<ReturnEligibility>(t, `/orders/${enc(order)}/return-eligibility`),
  create: (t: string, body: unknown) => post<ReturnDetail>(t, "/returns", body),
  list: (t: string, query: Query) => get<Paged<ReturnSummary>>(t, "/returns", query),
  detail: (t: string, number: string) => get<ReturnDetail>(t, `/returns/${enc(number)}`),
  cancel: (t: string, number: string, note: string | null) =>
    post<ReturnDetail>(t, `/returns/${enc(number)}/cancel`, { note }),

  adminList: (t: string, query: Query) =>
    get<Paged<AdminReturnSummary>>(t, "/admin/returns", query),
  adminDetail: (t: string, number: string) =>
    get<AdminReturnDetail>(t, `/admin/returns/${enc(number)}`),
  adminAction: (t: string, number: string, action: string, body: unknown) =>
    post<AdminReturnDetail>(t, `/admin/returns/${enc(number)}/${action}`, body),
  attention: (t: string) => get<AttentionCounts>(t, "/admin/attention"),
};

export const supportApi = {
  list: (t: string, query: Query) =>
    get<Paged<ConversationSummary>>(t, "/support/conversations", query),
  create: (t: string, body: unknown) => post<ConversationDetail>(t, "/support/conversations", body),
  detail: (t: string, number: string) =>
    get<ConversationDetail>(t, `/support/conversations/${enc(number)}`),
  close: (t: string, number: string) =>
    post<ConversationDetail>(t, `/support/conversations/${enc(number)}/close`),
  reopen: (t: string, number: string) =>
    post<ConversationDetail>(t, `/support/conversations/${enc(number)}/reopen`),
  unread: (t: string) => get<{ unread: number }>(t, "/support/unread-count"),

  adminList: (t: string, query: Query) =>
    get<Paged<AdminConversationSummary>>(t, "/admin/support/conversations", query),
  adminDetail: (t: string, number: string) =>
    get<AdminConversationDetail>(t, `/admin/support/conversations/${enc(number)}`),
  adminClose: (t: string, number: string) =>
    post<AdminConversationDetail>(t, `/admin/support/conversations/${enc(number)}/close`),
  adminReopen: (t: string, number: string) =>
    post<AdminConversationDetail>(t, `/admin/support/conversations/${enc(number)}/reopen`),
};
