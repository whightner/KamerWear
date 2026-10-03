# Database

KamerWear uses **PostgreSQL**, accessed through **SQLAlchemy 2.x** with the
psycopg 3 driver. **Alembic** manages the schema.

## Connection

The backend reads `DATABASE_URL` from the environment or `backend/.env`:

```
DATABASE_URL=postgresql+psycopg://postgres:CHANGE_ME@localhost:5432/kamerwear
```

Create the database once:

```bash
psql -U postgres -c "CREATE DATABASE kamerwear;"
```

## Catalog schema

```
categories ──< products ──< product_images
                   │
                   └──< product_variants ──── inventory (one row per variant)
```

| Table | Purpose | Notes |
| --- | --- | --- |
| `categories` | Shoes, Clothing, Accessories | unique `slug`; `is_active` hides a category and its products |
| `products` | One catalog item | unique `slug`; `gender` is `men`/`women`/`unisex` (a field, not a category); `base_price` and `compare_at_price` are integer XAF; `rating_average`/`review_count` are seeded demo data |
| `product_images` | Ordered photos | `image_path` points to a frontend static file (`/images/products/...`); `position` sets the order (ties broken by id); optional `color_name` links a photo to a colour |
| `product_variants` | Sellable colour + size | unique `sku` (e.g. `UR02-BLACK-43`); `size` is null for one-size products; `price_override` is optional, otherwise the product price applies |
| `inventory` | Stock for one variant | `on_hand` and `reserved`; available = `on_hand - reserved`, never reported below 0 |

Derived values (discount percent, effective variant price, availability) are
computed in code, not stored, so there is one source of truth.

Not in the MVP: stock movement history, warehouses, reviews.

## Accounts schema

```
users ──── user_profiles (one per user)
  │
  └──< auth_sessions (one per signed-in device)
```

| Table | Purpose | Notes |
| --- | --- | --- |
| `users` | Login identity | unique `email` (stored trimmed and lower-cased); `password_hash` is Argon2id, never plaintext; `role` is `customer` or `admin` (check constraint); `is_active`, `is_verified` (false until email verification exists); `created_at`, `updated_at`, `last_login_at` |
| `user_profiles` | Personal details | `user_id` unique, cascades on delete; `first_name`, `last_name`, optional `phone` (normalised, e.g. `+237699123456`), `avatar_path` (unused for now) |
| `auth_sessions` | Revocable login sessions | UUID `id` (the `sid` claim in tokens); `refresh_jti` is the only refresh token currently valid; `expires_at`, `last_used_at`, `revoked_at` (set on logout, password change or refresh-token reuse) |

Expired and revoked sessions are kept; a cleanup job can come later.

Favorites are still kept in the browser only.

## Commerce schema

```
users ──< addresses
  │
  ├──── carts (one per user) ──< cart_items >── product_variants
  │
  └──< orders ──< order_items          (snapshots; variant/product ids kept for reference)
          └───< order_status_history
```

| Table | Purpose | Notes |
| --- | --- | --- |
| `addresses` | Saved delivery addresses | `label`, `recipient_name`, `phone`, `country_code` (`CM`), `region`, `city`, `quarter`, `street_or_landmark`, optional `latitude`/`longitude`; partial unique index `uq_addresses_user_id_default` allows one default per user |
| `carts` | One saved cart per customer | unique `user_id` |
| `cart_items` | Cart lines | `variant_id` + `quantity` only (`quantity > 0`, unique per cart and variant); prices and names are never stored here |
| `orders` | Placed orders | random unique `order_number` (`KW-2026-7K4M9Q`); `status`, `payment_status`, `payment_method` (check constraints); integer XAF `subtotal`, `delivery_fee`, `discount_total`, `total`; `delivery_*` columns copy the address; unique (`user_id`, `idempotency_key`) |
| `order_items` | Purchase-time line snapshots | product name, slug, SKU, size, colour, image path, `unit_price`, `quantity`, `line_total`; `product_id`/`variant_id` kept for reference (`SET NULL` if ever deleted) |
| `order_status_history` | Status events | `status`, optional customer-visible `note`, staff-only `internal_note`, `changed_by_user_id` (the admin; null for checkout), `created_at`; first row written when the order is placed |
| `payment_status_history` | Manual (demo) payment changes | `from_status`, `to_status`, optional staff `note`, `changed_by_user_id`, `created_at` |

Placing an order reserves stock (`inventory.reserved += quantity`); delivering
moves it out (`on_hand` and `reserved` drop) and cancelling releases it
(`reserved` drops). Staff change only `on_hand`, never below `reserved`. See
[../architecture/admin.md](../architecture/admin.md) for the order state
machine, and
[../architecture/commerce.md](../architecture/commerce.md) for the inventory
policy and row locking.

## Visual search schema

| Table | Purpose | Notes |
| --- | --- | --- |
| `product_image_embeddings` | One embedding per product photo and model | `product_image_id` (cascade delete), `model_name` (unique together), `dimensions`, `embedding` (L2-normalised float32 bytes, 2 KB for 512 numbers), `source_path` and `source_sha256` (what was encoded, for stale detection) |
| `visual_search_index_runs` | Log of index builds | `trigger` (cli/admin), `status`, indexed/unchanged/failed/removed counts, `started_at`, `finished_at` |

No pgvector: the ~70 vectors are compared with NumPy (see
[../architecture/visual-search.md](../architecture/visual-search.md)).
Uploaded search photos are never stored.

## Smart Fit schema

| Table | Purpose | Notes |
| --- | --- | --- |
| `fit_profiles` | The customer's confirmed sizes (one per user, cascade delete) | `height_cm`, `fit_preference` (slim/regular/relaxed), `top_size`, `bottom_size`, `shoe_size_eu` (entered by the customer), `estimated_*_cm` (NUMERIC(5,1), null when not estimated or manual), `source`, `confidence`, `estimation_version`, `confirmed_by_user`, timestamps |
| `fit_estimates` | Recent photo estimates awaiting confirmation (last 3 per user) | derived numbers only: height, preference, `used_side_photo`, estimated dimensions, suggested sizes, `confidence`, `warnings` (JSON), `estimation_version` |

No table stores photos, landmarks or masks. Deleting the Fit Profile deletes
the user's estimates too.

## Returns and support schema

| Table | Purpose | Notes |
| --- | --- | --- |
| `return_requests` | One return request | `return_number` (unique, e.g. KR-2026-8M4PQ2), `user_id`, `order_id` (cascade), `status` (requested/approved/rejected/received/refunded/cancelled, indexed), `reason_summary`, `customer_note`, `return_value` (integer XAF, purchase-time prices, no delivery fee), `refunded_amount` (demo record), `created_at`, `updated_at`, `resolved_at` |
| `return_items` | Returned lines | `order_item_id` (the immutable order snapshot: name, SKU, size, price), `quantity > 0`, `reason`, `condition_note`, `restock` (staff decision when received); unique per request and order line |
| `return_status_history` | Audit trail | `status`, `actor_user_id`, `customer_note` (shown to the customer), `internal_note` (staff only), `created_at` |
| `support_conversations` | Customer ↔ store threads | `conversation_number` (KS-…), `user_id`, optional `order_id` / `return_request_id` (set null if removed), `subject`, `status` (open/closed), `last_message_at` (indexed, for sorting), `closed_at` |
| `support_messages` | Plain-text messages | `conversation_id`, `sender_user_id`, `sender_role` (customer/store, set by the endpoint), `body`, `created_at`, `read_at`; index `(conversation_id, id)` for "messages after id N" polling |

No uploaded files are stored. The delivery date used for the return window is
the `delivered` row of `order_status_history`.

## Seed data

```bash
python -m app.db.seed
```

Loads the demo catalog (3 categories, 19 products, 69 images, 189 variants)
from `backend/app/db/seed_data/catalog.json`, the single source of demo
catalog data (the storefront has no product data of its own). It is idempotent: rows are matched
by slug or SKU and updated, so running it again never duplicates data.
Inventory is reset to the demo stock levels (low stock, sold-out sizes and one
out-of-stock product, as in the storefront).

Re-running the seed resets inventory to the demo levels, which also drops
stock reserved by existing orders. Use it on development databases only.

The seed never creates users or orders. Create an admin with
`python -m app.db.create_admin` (see [../architecture/auth.md](../architecture/auth.md)).

## Migrations

Run these from `backend/` with the virtualenv active:

```bash
alembic upgrade head                              # apply all migrations
alembic revision --autogenerate -m "add products" # create a migration from model changes
alembic downgrade -1                              # undo the last migration
alembic current                                   # show the applied revision
```

Always read an autogenerated migration before applying it.

For a model to be detected, it must inherit from `app.db.base.Base` and be
imported in `app/models/__init__.py`.

## Tests

Database tests use a separate database: `TEST_DATABASE_URL` if set, otherwise
`DATABASE_URL` with `_test` added to the name (e.g. `kamerwear_test`, created
automatically). The schema is rebuilt with the real migrations on each run.
If PostgreSQL is not running, those tests are skipped.

## Conventions

- **Money**: integer columns holding whole XAF (FCFA). Never use floats.
- **Constraint names**: generated by the naming convention in `app/db/base.py`
  (`pk_<table>`, `uq_<table>_<column>`, `fk_<table>_<column>_<referred_table>`, …)
  so migrations stay predictable.
- **Timestamps**: timezone-aware and stored in UTC.
- **Schema changes**: only through Alembic migrations, never by hand.
