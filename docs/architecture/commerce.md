# Cart, checkout, orders and tracking

Task 007 makes the shopping journey work end to end:

```
Product → Cart → Delivery address → Checkout → Order → Status / tracking
```

It is still a demo: **no real payment provider or courier is connected.**

## The server is the source of truth

The browser only says *which* variant, *how many*, *which* saved address and
*which* payment method. FastAPI decides everything else:

| Value | Decided by |
| --- | --- |
| Cart owner, order owner, address owner | the access token (never a `user_id` from the client) |
| Unit price | the catalog: variant `price_override`, else product `base_price` (sale prices included) |
| Stock | `inventory.on_hand - inventory.reserved`, re-read and locked at order time |
| Delivery fee | `app/services/delivery.py` from the address city |
| Discount, total | the server (`discount_total` is 0: no promo codes yet) |

Request bodies reject unknown fields (`extra="forbid"`), so a client can't
even send `price`, `total`, `delivery_fee` or `user_id`.

## Cart

- **Signed in:** one saved cart per customer (`carts` / `cart_items`). Lines
  store only `variant_id` and `quantity`; names, images, prices and stock are
  read from the catalog every time the cart is shown. A reload, logout/login
  or another device shows the same cart.
- **Stock rule:** adding or increasing a line may not exceed the available
  stock (`409 insufficient_stock`, e.g. *"Only 1 item remains for Urban Runner
  02, EU 43."*) or 10 per line (`409 quantity_limit`). Lowering a quantity is
  always allowed.
- If stock drops after an item was added, the line shows an `issue`
  ("Only 1 left. Reduce the quantity to continue.") and checkout is blocked
  until it is fixed.
- The web app has one cart source at a time: the saved cart when signed in,
  otherwise the guest cart. The header count, product page and cart page all
  read the same state.

### Guest cart and merge

- Visitors who aren't signed in keep a **temporary cart in browser memory**
  (as before). It survives navigation but not a full page reload.
- Checkout requires an account: "Proceed to checkout" (or "Buy Now") leads to
  `/login?next=/checkout`.
- The login and register forms send the guest lines (variant id and quantity
  only, never prices) with the form. After signing in, the server merges them
  (`POST /cart/merge`): duplicate variants are combined, quantities are capped
  at current stock (and 10), unavailable items are skipped, and prices come
  from the catalog.
- If anything couldn't be added in full, the next page shows a notice ("some
  items were sold out or limited by current stock") with a link to the cart.

## Addresses

Cameroon-style delivery addresses: label, recipient, phone, **region** (one of
the ten regions), **city**, **quarter / neighbourhood** and **street or precise
landmark** ("Near Tradex, blue gate"). There are no street-number or postcode
fields. `country_code` is `CM`; latitude/longitude are optional and no map
provider is used.

- Customers only ever see and change their own addresses; another customer's
  address id answers `404 address_not_found`.
- At most one default address (partial unique index). The first address is the
  default; making another one default clears the previous one; deleting the
  default promotes the newest remaining address.
- Addresses can be managed at `/account/addresses` or added inline at checkout.

## Delivery fee (demo rule)

A flat fee per destination city, calculated only by the server:

| City | Fee |
| --- | --- |
| Douala | 1 500 FCFA |
| Yaoundé | 2 000 FCFA |
| Bafoussam | 2 500 FCFA |
| Any other city | 3 500 FCFA |

City names are compared without accents or case. This is not a logistics
engine; a real courier quote can replace `delivery_fee()` later.

## Checkout

1. **Quote** — `POST /checkout/quote` with the chosen `address_id` and
   `payment_method`. It returns the lines, subtotal, delivery fee, discount and
   total, plus `issues` (empty cart, stock problems, missing choices) and
   `can_place_order`. It changes nothing. The checkout page re-quotes whenever
   the address or payment method changes.
2. **Place order** — `POST /orders` with the same choices, the total the
   customer saw (`expected_total`) and an `Idempotency-Key` header.

### What placing an order does (one transaction)

1. Lock the customer's cart row (serialises a double-click).
2. If an order with this idempotency key exists, return it (`200`).
3. Load the cart and the (owned) address.
4. Lock the inventory rows of the cart's variants (`SELECT … FOR UPDATE`, in
   variant-id order to avoid deadlocks) and re-check every quantity.
5. Calculate prices, delivery fee and total on the server. If the total
   differs from `expected_total`, stop with `409 quote_changed` so the customer
   reviews the new total first.
6. Create the order with a **copy of the address** and **snapshot lines**
   (product name, slug, SKU, size, colour, image, unit price, quantity, line
   total).
7. Reserve stock: `inventory.reserved += quantity`.
8. Record the first status event (`pending`, "Order placed.").
9. Empty the cart and commit.

Any error rolls everything back: no order, no reservation, cart unchanged.

### Concurrency

Two customers buying the last unit: the second checkout waits on the locked
inventory row, then re-reads it after the first commits, sees 0 available and
gets `409 insufficient_stock`. This is covered by a test with real concurrent
PostgreSQL connections (`tests/test_checkout_concurrency.py`); removing the
row locks makes that test fail.

### Double submission (idempotency)

The checkout page generates a random key once per visit and sends it as
`Idempotency-Key`. Orders store it with a unique `(user_id, idempotency_key)`
constraint. A repeated or simultaneous submit with the same key waits on the
cart lock and then returns the first order instead of creating another. The
"Place order" button is also disabled while submitting, but the server rule is
what guarantees it. Mobile clients can use the same header.

## Payment methods (demo)

`mobile_money`, `card` and `cash_on_delivery` are **demo choices**. No payment
provider is called, no card number, CVV or Mobile Money PIN is requested or
stored, and only the chosen method is saved. Every new order has
`payment_status = pending`; the UI says "Payment pending (demo — no payment
taken)" for Mobile Money and Card and "To pay on delivery" for cash. Nothing
ever shows as paid.

## Inventory policy

| Event | `on_hand` | `reserved` | available |
| --- | --- | --- | --- |
| Order placed | — | `+ qty` | `- qty` |
| Order delivered | `- qty` | `- qty` | unchanged |
| Order cancelled | — | `- qty` | `+ qty` |

Stock is never counted twice, and `available = on_hand - reserved` stays
correct throughout. (Re-running the demo seed resets inventory, including
reservations; it's for development only.)

## Order numbers

`KW-<year>-<6 characters>`, e.g. `KW-2026-7K4M9Q`, from an unambiguous alphabet
(no 0/O/1/I/L). They are random, so they don't reveal how many orders exist
and can't be guessed in sequence; a unique index guarantees no duplicates.
Lookups are case-insensitive. Internal database ids are never shown.

## Statuses and tracking

Order status: `pending` → `confirmed` → `preparing` → `shipped` →
`out_for_delivery` → `delivered`, or `cancelled`.
Payment status: `pending`, `paid`, `failed`, `refunded`.

Every change is recorded in `order_status_history`. The order response
includes a `timeline` with the six steps marked `done`, `current` or
`upcoming` (with the time each was reached). This is **status tracking, not
GPS**: no courier map is shown.

- `/orders` lists the customer's orders, newest first.
- `/orders/{number}` shows one order (also the success page after checkout).
- `/orders/track` (the header's "Track order") looks up an order number. It
  only finds the signed-in customer's own orders; anyone else's number answers
  exactly like a number that doesn't exist.

Staff move orders along the timeline in the store admin (`/admin/orders`);
see [admin.md](admin.md) for the allowed transitions. The same rules apply
from the command line:

```bash
cd backend
python -m app.db.set_order_status KW-2026-7K4M9Q shipped --note "Left the Douala hub"
```

## Not included

Real MTN MoMo / Orange Money / card payments, courier APIs, GPS tracking,
returns, refunds, promo codes and persistent favorites.
