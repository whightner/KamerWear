# Returns and customer support

Task 011 adds the after-sales side: customers request returns for delivered
items, store staff process them, and both sides talk in support
conversations.

```
Order delivered ──► Return request ──► Store review ──► Return processing
                    (customer)          (admin)          (receive, restock, demo refund)

Customer ◄──── support conversation (REST + polling, PostgreSQL) ────► Store/Admin
```

## For the presentation (short explanations)

> **Returns.** KamerWear checks every return request against the customer's
> own delivered order: the order must be delivered, the request must be within
> 7 days of the delivery recorded in the order history, and the quantity can't
> exceed what was bought minus what is already being returned. The value comes
> from the price paid at purchase time. Store staff then approve or reject the
> request, mark the parcel received while choosing which items can be sold
> again (those go back into stock, exactly once), and record the refund. The
> refund is a demo/manual record: no payment provider is contacted.
>
> **Support.** Customer support uses authenticated conversations stored in
> PostgreSQL. While a conversation is open, the page asks the server every 4
> seconds for messages newer than the last one it has. This keeps deployment
> simple (no WebSocket server, Redis or chat service) while customers still
> see replies within a few seconds.

## Return policy (what the code enforces)

| Rule | Where |
| --- | --- |
| Order status must be `delivered` | `services/returns.check_eligibility` |
| Within `RETURN_WINDOW_DAYS` = 7 days of the **delivery** time (latest `delivered` row in `order_status_history`), never the order date | same |
| Per order line: at most purchased − quantity in requests that are `requested`, `approved`, `received` or `refunded` (rejected/cancelled requests free the quantity) | `create_return` |
| The order row is locked (`SELECT … FOR UPDATE`) while a request is created, so two simultaneous requests can't over-return | `create_return` |
| Owner, prices and totals are never accepted from the browser (`extra="forbid"`; the server reads the customer's own order) | `schemas/returns.py` |
| Value = purchase-time `unit_price × quantity` from the immutable order lines; delivery fee not included | `create_return` |

Customer-readable version: `/help/returns`.

## Return states

```
requested ──► approved ──► received ──► refunded
    ├──► rejected
    └──► cancelled  (customer, only while requested)
```

Terminal: `rejected`, `refunded`, `cancelled` (`resolved_at` is set). Any other
move → `409 invalid_return_transition`. Each change locks the return row and
re-reads it first, so a repeated or simultaneous request finds the new status
and is rejected. Every change adds a `return_status_history` row with the
actor, an optional customer-visible note and an optional internal note
(never returned by customer endpoints).

## Inventory and refunds

| Step | Inventory | Money |
| --- | --- | --- |
| requested / approved / rejected / cancelled | no change | — |
| received | for each line marked **Restockable**: `inventory.on_hand += quantity` (rows locked); **Not restockable** (e.g. damaged): no change. `reserved` is never touched (the order is already delivered). Every line needs an explicit decision (`422 restock_decision_required`) | — |
| refunded | — | `refunded_amount = return_value` recorded. **Demo/manual: no Mobile Money, Orange Money or card refund is executed.** Both customer and admin pages say so |

Optionally, when every unit of a **paid** order has been refunded through
returns, staff may also mark the order payment `refunded` (the existing manual
payment state). Partial returns can't (`409 order_not_fully_returned`).

A test runs two simultaneous "receive" calls on separate connections: one
succeeds, the other gets `invalid_return_transition`, and stock rises once.

## Support architecture

```
Browser ──(poll every 4 s: GET …/messages?after_id=N)──► Next.js route handler
        ──(send: POST …/messages)─────────────────────►   (adds Bearer from HttpOnly cookie)
                                                          ──► FastAPI ──► PostgreSQL
```

- **Conversations** (`KS-2026-XXXXXX`): subject (sizing, delivery, order
  issue, return question, other), status `open`/`closed`, optional link to one
  of the customer's own orders or returns (a return also links its order).
- **Messages**: plain text, 1–2 000 characters (`message_empty`,
  `message_too_long`; requests over 10 000 characters are refused outright).
  Stored exactly as typed and rendered as escaped text by React (no HTML
  rendering anywhere), so `<script>` shows as text. Tests check both.
- **Sender role** comes from the endpoint: customer endpoints always write
  `customer`, admin endpoints `store`. A customer can't post as the store.
  Store replies are shown as "KamerWear support".
- **Closed** conversations refuse new messages (`409 conversation_closed`);
  the customer or staff can reopen them.
- **Rate limit**: 30 new conversations + messages per minute per user
  (in-memory, single process, like the other limits).
- **Attachments**: none. Chat is text-only, and return requests have no photo
  upload: there is no safe storage layer yet. *Photo evidence is planned for
  production storage integration.*

### Polling

- Only on an open conversation page (customer or admin), every 4 s, and not
  while the tab is hidden.
- One request at a time (no overlap); stops when the page unmounts.
- Asks only for messages **after the last id** it has (`support_messages`
  has an index on `(conversation_id, id)`); a first load returns the latest
  200 messages.
- A failed poll keeps the messages already shown and shows "Connection
  problem"; the next poll retries.
- If the access token expired (route handlers skip the session proxy), the
  page calls a Server Action that renews the session once, then retries.
- New messages from the other side are announced in an `aria-live` region.
- Polling uses route handlers, not Server Actions, because Next.js runs a
  client's Server Actions one at a time (a poll would delay a send).

### Read state

`support_messages.read_at` is set when the other side loads the conversation
(customer reads store messages, staff read customer messages). The account
menu shows the customer's unread store replies ("Support 2"); the admin
sidebar shows returns to process (requested or approved) and conversations
with unread customer messages (`GET /api/v1/admin/attention`).

## Pages

| Route | Who | Purpose |
| --- | --- | --- |
| `/orders/[n]` | customer | "Request a return" (if eligible), "Contact support", returns of this order |
| `/orders/[n]/return` | customer | choose items, quantity, reason, details → review → submit; explains why when not eligible |
| `/account/returns` | customer | returns, newest first (number, order, date, status, items, value) |
| `/returns/[n]` | customer | items, reasons, notes, status history, demo refund note, cancel, contact support |
| `/support`, `/support/new`, `/support/[n]` | customer | conversations; new (optionally `?order=` / `?return=`); conversation with polling |
| `/admin/returns`, `/admin/returns/[n]` | admin | filters (status, search, dates); detail with customer, order, prices, history incl. internal notes, next-step forms |
| `/admin/support`, `/admin/support/[n]` | admin | filters (open/closed, unread, search); conversation with order/return context |
| `/help/returns`, `/help/contact` | everyone | policy as implemented; contact = support conversations (no fake phone/email) |

All customer routes are behind the login proxy and ownership is checked by
the API: another customer's return or conversation answers 404, exactly like
a missing one. Admin routes require the ADMIN role (403 for customers).

## Known limitations

- Polling, not push: replies appear within ~4 s while the page is open; no
  email/SMS/push notifications.
- Text-only chat; no photo evidence for returns.
- Refunds are manual records; no payment provider integration, no courier
  pickup, no warehouse logistics. Delivery fees are never refunded.
- One return window for all products; no exchanges (customers can ask in
  support and order again).
- Unread state is per message for the "other side" as a whole (no per-staff
  read tracking).
- In-memory rate limits reset on restart and aren't shared between workers.
