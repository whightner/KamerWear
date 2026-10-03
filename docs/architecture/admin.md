# Store admin

Task 008 adds the store-owner side: a dashboard, product, category, variant,
image and inventory management, and order fulfilment. Store staff no longer
need to edit seed files or run SQL.

## Creating an admin

There is no public admin sign-up and no demo admin in the code. A developer
creates one from the backend directory, typing the details at the prompts:

```bash
cd backend
python -m app.db.create_admin
```

or non-interactively (for scripts; values come from your shell, never from the
repository):

```bash
ADMIN_EMAIL=... ADMIN_FIRST_NAME=... ADMIN_LAST_NAME=... ADMIN_PASSWORD=... python -m app.db.create_admin
```

The admin then logs in at `/login` like anyone else; the account menu shows
**Store admin**, which opens `/admin`. A customer account is never promoted
automatically.

## Authorization

- **API (the real protection).** Every `/api/v1/admin/*` route depends on
  `require_admin` (`backend/app/api/deps.py`): no token → `401
  authentication_required`; a customer's token → `403 admin_required`. Tests
  call every admin route as a visitor and as a customer, and check that a
  forbidden request changes nothing.
- **Web app.** `proxy.ts` sends signed-out visitors of `/admin*` to `/login`.
  The admin layout checks the role on the server before rendering: customers
  get a "Not authorized" page, and admin pages fetch nothing for them, so no
  admin content is ever sent to a customer's browser.

## Admin routes

| Route | Purpose |
| --- | --- |
| `/admin` | Dashboard |
| `/admin/products` | Product list: search (name, slug, SKU), category, active/inactive, low stock |
| `/admin/products/new` | Step 1: create a product (starts inactive) |
| `/admin/products/[id]` | Step 2: status, variants and stock, images, details |
| `/admin/categories` | Categories with product counts |
| `/admin/inventory` | Stock per variant, with filters |
| `/admin/orders` | All orders, filters by status, payment status, city and search |
| `/admin/orders/[orderNumber]` | Order details, fulfilment, payment state, history |
| `/admin/visual-search` | Visual search index status and "Update visual index" |

## Dashboard

Figures come from SQL aggregates (`GET /api/v1/admin/overview`):
orders awaiting action (pending, confirmed or preparing), orders today
(Africa/Douala calendar day), orders in delivery, customers (customer
accounts only), active/inactive products, active variants, low-stock and
out-of-stock variants, plus the five latest orders and the variants most in
need of restocking.

**Order value** is the sum of all non-cancelled order totals. It is *not*
called revenue, because demo payments are mostly unpaid. "Marked paid (demo)"
shows the total of orders whose manual payment status is `paid`.

## Product lifecycle

1. **Create** the product (name, slug, category, gender, type, price,
   optional compare-at price, merchandising flags, keywords). It starts
   **inactive**, so half-finished products never reach the shop.
2. **Add variants** (SKU, size, colour name and swatch, optional price
   override, starting stock).
3. **Add images** (paths to existing files, alt text, position, colour).
4. **Activate.** The product appears in `/shop` and on its page with real
   stock.

Nothing is hard-deleted. Deactivating a product hides it from the shop and
makes it unbuyable (cart and checkout reject it), while it stays editable in
the admin and past orders keep their snapshots. Reactivating restores it if
its category is active too (the admin shows "Active, but hidden: category
inactive" otherwise).

Rules enforced by the API:

- Slugs are unique per table and look like `kribi-linen-shirt`
  (`slug_already_exists` on conflict).
- Prices are integer FCFA, 0–10 000 000. Floats (`18500.5`, even `18500.0`) and
  strings are rejected rather than rounded. A compare-at price must be higher
  than the price, or empty.
- Rating and review count are seeded demo data and can't be edited.

## Categories

Name, slug (unique), description and active flag. Deactivating hides the
category and all its products from the shop (existing storefront rule); data
and orders are kept. No delete endpoint.

## Variants

SKU (unique, stored upper-case, `sku_already_exists`), size (empty = one
size), colour name and hex swatch, optional price override and active flag.
One variant per colour + size per product (`variant_already_exists`), so the
shop's selectors stay unambiguous. Variants are deactivated, never deleted:
inactive variants disappear from the product page and can't be added to a
cart or ordered; order history keeps its own copy of SKU, size and colour.

## Images (metadata only)

Product photos are static files of the web app in
`frontend/public/images/products/`. The admin manages which files a product
uses: path, alt text, position and optional colour. There is **no upload**:
real uploads need object storage (planned with the media service) and
wouldn't survive redeploys of the current app.

Paths must match `/images/products/<folder>/<file>.(webp|jpg|jpeg|png|avif)`;
anything else (other folders, `..`, absolute URLs, other extensions) is
rejected. The gallery is ordered by position, then by id, so equal positions
are still deterministic. Removing an image deletes its metadata, not the file.

## Inventory

| Field | Who changes it |
| --- | --- |
| `on_hand` | Staff, on `/admin/inventory` or the product page |
| `reserved` | Orders only (placing reserves; delivering or cancelling releases) — read-only in the admin and rejected by the API |
| available | `on_hand − reserved`, computed |

`on_hand` can never go below `reserved`: the API rejects it with
`409 inventory_below_reserved`, e.g. *"Cannot set on-hand stock to 2 because
4 units are reserved by orders."* The inventory row is locked during the
update so a checkout can't reserve in between.

**Low stock** = 1–5 units available (`LOW_STOCK_THRESHOLD` in
`backend/app/core/config.py`, the same rule as the shop's "Only N left").
**Out of stock** = 0 available. Filters: search (product, SKU, colour),
product, low stock, out of stock; inactive products/variants are hidden unless
requested. No warehouses.

## Order state machine

```
pending ──► confirmed ──► preparing ──► shipped ──► out_for_delivery ──► delivered
   │            │             │
   └────────────┴─────────────┴──► cancelled
```

| From | Allowed next |
| --- | --- |
| pending | confirmed, cancelled |
| confirmed | preparing, cancelled |
| preparing | shipped, cancelled |
| shipped | out_for_delivery |
| out_for_delivery | delivered |
| delivered | — (terminal) |
| cancelled | — (terminal) |

Orders can't be cancelled once handed to the courier (shipped); returns are a
later task. Anything else is rejected with `409 invalid_order_transition`
(the message lists the allowed next statuses). The admin form only offers the
allowed ones.

### Inventory effects (exactly once)

| Transition | Inventory |
| --- | --- |
| order placed (Task 007) | `reserved += qty` |
| → delivered | `on_hand −= qty`, `reserved −= qty` |
| → cancelled | `reserved −= qty` |

The order row is locked (`SELECT … FOR UPDATE`) and re-read before a change,
so a repeated or simultaneous request finds the new status and is rejected:
stock can't be released or deducted twice. A test runs two concurrent
cancellations and checks that one fails and stock moves once.

### History and notes

Every transition adds an `order_status_history` row with the admin who made
it, an optional **customer note** (shown on the customer's order page) and an
optional **internal note** (staff only, never returned by customer APIs).
The customer's `/orders/[number]` and `/orders/track` read the same order and
history, so they show admin updates immediately.

## Payment status (demo / manual)

No payment provider is connected. Staff record what happened; the admin page
labels it "Demo/manual payment state" and no money moves.

| From | Allowed next |
| --- | --- |
| pending | paid, failed |
| failed | pending (retry), paid |
| paid | refunded |
| refunded | — |

A cancelled order can only go `paid → refunded`. Other changes are rejected
with `409 invalid_payment_transition`. Each change is logged in
`payment_status_history` with the admin and an optional staff note.

## Visual search index

New or changed product photos are not searchable by image until the index is
updated. The dashboard shows a "Visual search" card (ready / update needed),
`/admin/visual-search` lists unindexed, changed and missing photos with an
**Update visual index** button, and the product editor marks photos that
aren't indexed yet. See [visual-search.md](visual-search.md).

## Not included

Real payments (MTN MoMo, Orange Money, cards), courier APIs, GPS tracking,
returns/refunds workflow, customer administration, image upload, promotions,
multi-vendor sellers.
