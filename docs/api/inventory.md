# API inventory (v1.0.0-demo)

All endpoints live under `/api/v1` on the FastAPI service (except `GET /`, the
service identification). Generated from the OpenAPI schema
(`http://localhost:8000/docs`); request and response details are in
[README.md](README.md) and the interactive docs.

Access: **public**, **customer** (any signed-in account; ownership comes from
the access token, and another customer's resource answers 404) or **admin**
(ADMIN role; customers get `403 admin_required`, visitors `401`).

## Health

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | public | Service and database liveness |

## Auth

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/auth/register` | public | Create a customer account (signed in) |
| POST | `/auth/login` | public | Email + password → access + refresh tokens |
| POST | `/auth/refresh` | public (refresh token) | Rotate tokens; reuse of an old token revokes the session |
| POST | `/auth/logout` | public (refresh token) | Revoke the session |

## Users (account)

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/users/me` | customer | Signed-in user and profile |
| PATCH | `/users/me` | customer | Update name and phone |
| POST | `/users/me/change-password` | customer | Change password; signs out other sessions |

## Catalog

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/categories` | public | Active categories |
| GET | `/products` | public | Search, filters, sorting, pagination |
| GET | `/products/{slug}` | public | Product detail with variants and stock |
| GET | `/products/{slug}/similar` | public | Rule-based related products |

## Cart

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/cart` | customer | Cart with current prices and stock |
| POST | `/cart/items` | customer | Add a variant |
| PATCH | `/cart/items/{item_id}` | customer | Change quantity |
| DELETE | `/cart/items/{item_id}` | customer | Remove a line |
| DELETE | `/cart` | customer | Empty the cart |
| POST | `/cart/merge` | customer | Merge the guest cart after login (ids and quantities only) |

## Addresses

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/addresses` | customer | My addresses |
| POST | `/addresses` | customer | Add an address |
| PATCH | `/addresses/{address_id}` | customer | Update |
| DELETE | `/addresses/{address_id}` | customer | Delete |

## Checkout and orders

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/checkout/quote` | customer | Server-calculated subtotal, delivery fee and total |
| POST | `/orders` | customer | Place an order (Idempotency-Key header; reserves stock) |
| GET | `/orders` | customer | My orders |
| GET | `/orders/{order_number}` | customer | Order detail and tracking timeline |

## Returns

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/orders/{order_number}/return-eligibility` | customer | Eligibility and returnable quantities |
| POST | `/returns` | customer | Request a return |
| GET | `/returns` | customer | My returns |
| GET | `/returns/{return_number}` | customer | Return detail (customer notes only) |
| POST | `/returns/{return_number}/cancel` | customer | Cancel while requested |

## Support

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/support/conversations` | customer | My conversations |
| POST | `/support/conversations` | customer | Start one (optionally about my order/return) |
| GET | `/support/conversations/{number}` | customer | Conversation (marks store messages read) |
| GET | `/support/conversations/{number}/messages?after_id=` | customer | Polling: newer messages only |
| POST | `/support/conversations/{number}/messages` | customer | Send a plain-text message |
| POST | `/support/conversations/{number}/close` / `reopen` | customer | Close / reopen |
| GET | `/support/unread-count` | customer | Unread store replies |

## Smart Fit

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/fit/estimate` | customer | Front (+ optional side) photo + height → estimate (not saved as profile) |
| GET | `/fit/profile` | customer | Confirmed Fit Profile |
| PUT | `/fit/profile` | customer | Confirm or edit (measurements copied from own estimate) |
| DELETE | `/fit/profile` | customer | Delete profile and estimates |
| GET | `/fit/size-charts` | public | Versioned demo size charts |
| GET | `/products/{slug}/fit-recommendation` | customer | Recommended size for a product |

## Visual search

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| POST | `/visual-search` | public | Photo → visually similar products (rate-limited) |
| GET | `/products/{slug}/visual-similar` | public | Products similar to a product's photos |

## Admin

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/admin/overview` | Dashboard figures |
| GET | `/admin/attention` | Sidebar badges (returns to process, unread conversations) |
| GET / POST | `/admin/categories` | List / create categories |
| PATCH | `/admin/categories/{category_id}` | Edit or (de)activate |
| GET / POST | `/admin/products` | List / create products (new ones start inactive) |
| GET / PATCH | `/admin/products/{product_id}` | Detail / edit or (de)activate |
| POST | `/admin/products/{product_id}/variants` | Add a variant with starting stock |
| PATCH | `/admin/variants/{variant_id}` | Edit or (de)activate a variant |
| POST | `/admin/products/{product_id}/images` | Add image metadata (no upload) |
| PATCH / DELETE | `/admin/images/{image_id}` | Edit / remove image metadata |
| GET | `/admin/inventory` | Stock per variant |
| PATCH | `/admin/inventory/{variant_id}` | Set on-hand stock (never below reserved) |
| GET | `/admin/orders` | All orders with filters |
| GET | `/admin/orders/{order_number}` | Order with internal history |
| POST | `/admin/orders/{order_number}/status` | Next status (state machine, stock adjusted once) |
| POST | `/admin/orders/{order_number}/payment-status` | Manual/demo payment state |
| GET | `/admin/returns` | All returns with filters |
| GET | `/admin/returns/{return_number}` | Return with internal history and next steps |
| POST | `/admin/returns/{return_number}/approve` / `reject` | Decide a requested return |
| POST | `/admin/returns/{return_number}/receive` | Received + per-line restock decision |
| POST | `/admin/returns/{return_number}/refund` | Record the demo/manual refund |
| GET | `/admin/support/conversations` | All conversations with filters |
| GET | `/admin/support/conversations/{number}` | Conversation with order/return context |
| GET / POST | `/admin/support/conversations/{number}/messages` | Poll / reply as the store |
| POST | `/admin/support/conversations/{number}/close` / `reopen` | Close / reopen |
| GET | `/admin/visual-search/status` | Visual index status |
| POST | `/admin/visual-search/rebuild` | Update the visual index |

All 34 admin operations are tested to return 401 for visitors and 403 for
customers (`backend/tests/test_authorization_matrix.py`).

## Next.js route handlers (same-origin, browser only)

| Path | Purpose |
| --- | --- |
| `POST /api/visual-search` | Forwards the search photo (public) |
| `POST /api/fit/estimate` | Forwards Smart Fit photos with the access token |
| `GET/POST /api/support/[number]/messages` | Customer chat polling and sending |
| `GET/POST /api/admin/support/[number]/messages` | Staff chat polling and replies |

The cookie-authenticated POST handlers reject requests whose `Origin` isn't the
site itself (CSRF defence in addition to SameSite=Lax cookies).
