# Architecture overview (v1.0.0-demo)

KamerWear is a **modular monolith**: one Next.js web app, one FastAPI
application and one PostgreSQL database. The two pretrained AI models run
inside the FastAPI process. There are no microservices, message queues, Redis
or external AI APIs; this keeps the academic demo simple to install and run.

```
                         ┌──────────────────────────┐
     Browser ──────────► │   Next.js web (frontend) │  pages, Server Actions,
   (phone / desktop)     │   + BFF route handlers   │  HttpOnly auth cookies
                         └────────────┬─────────────┘
                                      │ REST / JSON  (/api/v1, Bearer token)
                         ┌────────────▼─────────────┐
                         │     FastAPI (backend)    │  validation, business rules,
                         │                          │  authorization, rate limits
                         └──┬──────────┬─────────┬──┘
                            │          │         │
                ┌───────────▼──┐ ┌─────▼──────┐ ┌▼───────────────────┐
                │ PostgreSQL 18│ │ OpenCLIP   │ │ MediaPipe Pose     │
                │ business data│ │ ViT-B-32   │ │ Landmarker (heavy) │
                │ + embeddings │ │ visual     │ │ Smart Fit          │
                └──────────────┘ │ search     │ └────────────────────┘
                                 └────────────┘
               (models are local files, loaded lazily, CPU; optional packages)
```

## Modules

| Module | Backend | Web | Docs |
| --- | --- | --- | --- |
| Auth & accounts | `services/auth.py`, `endpoints/auth.py`, `users.py` | `/login`, `/register`, `/account/*`, `proxy.ts` | [auth.md](auth.md) |
| Catalog | `services/catalog.py`, `endpoints/products.py`, `categories.py` | `/`, `/shop`, `/product/[slug]` | [../api/README.md](../api/README.md) |
| Cart, addresses, checkout, orders | `services/cart.py`, `addresses.py`, `orders.py`, `delivery.py` | `/cart`, `/checkout`, `/orders/*`, `/account/addresses` | [commerce.md](commerce.md) |
| Admin | `services/admin_catalog.py`, `admin_store.py`, `endpoints/admin_*` | `/admin/*` | [admin.md](admin.md) |
| Returns | `services/returns.py`, `endpoints/returns.py`, `admin_returns.py` | `/orders/[n]/return`, `/account/returns`, `/returns/[n]`, `/admin/returns` | [returns-support.md](returns-support.md) |
| Support | `services/support.py`, `endpoints/support.py`, `admin_support.py` | `/support/*`, `/admin/support` | [returns-support.md](returns-support.md) |
| Visual search | `app/ai/*`, `services/visual_search.py` | `/visual-search`, "Find Similar" | [visual-search.md](visual-search.md) |
| Smart Fit | `app/fit/*`, `services/fit.py` | `/fit`, `/account/fit-profile`, product block | [smart-fit.md](smart-fit.md) |
| Demo tooling | `app/db/reset_demo.py`, `check_integrity.py`, `app/demo/healthcheck.py` | — | [../demo/README.md](../demo/README.md) |

## Layers

### Next.js (`frontend/`, App Router, TypeScript, Tailwind)

- Server Components fetch from the API on each request; the browser never
  talks to FastAPI directly.
- Auth tokens live only in HttpOnly, SameSite=Lax cookies; the Next.js server
  forwards the access token as a Bearer header. `proxy.ts` renews sessions and
  keeps signed-out visitors out of account, order, return, support and admin
  pages (the API enforces the same rules).
- Mutations use Server Actions (POST-only, Origin-checked by Next.js). A few
  route handlers act as a small BFF for uploads and chat polling; their
  cookie-authenticated POSTs check the Origin header too.
- No business rules: prices, totals, stock, eligibility and sizes come from
  the API. React escapes all text; no raw HTML is rendered anywhere.

### FastAPI (`backend/`)

| Package | Responsibility |
| --- | --- |
| `app/api/v1/endpoints/` | HTTP routes: parse input, call a service, return a schema |
| `app/schemas/` | Pydantic request/response models (`extra="forbid"` on inputs) |
| `app/services/` | Business logic, testable without HTTP |
| `app/models/` | SQLAlchemy 2 models |
| `app/ai/` | Visual search: image loading, OpenCLIP encoder, type guard, CLIs |
| `app/fit/` | Smart Fit: pose backend, measurement geometry, size charts |
| `app/core/` | Settings, password hashing/JWT, in-memory rate limits |
| `app/db/` | Sessions, seed, admin creation, demo reset, integrity checks |

Errors are structured `{"detail": {"code", "message"}}`; stack traces are
never returned.

### PostgreSQL 18

The single source of truth (24 tables, Alembic migrations). Money is stored as
integer XAF. Visual-search embeddings are float32 bytes in the same database
(about 70 vectors; NumPy computes similarities in memory). See
[../database/er.md](../database/er.md).

### AI models (optional)

- **OpenCLIP ViT-B-32 / laion2b_s34b_b79k**: image and text embeddings for
  visual search. Weights (~600 MB) downloaded once by
  `python -m app.ai.prepare_visual_search`.
- **MediaPipe Pose Landmarker heavy** (30.7 MB, SHA-256 pinned): body
  landmarks and outline for Smart Fit, prepared by
  `python -m app.ai.prepare_smart_fit`.

Both load lazily on first use, run on CPU, never download at request time
and fail closed (`visual_search_unavailable` / `fit_service_unavailable`)
without fake fallback results. Neither is trained on customer photos.

## Request flow example (placing an order)

1. The checkout page (Server Component) loads the cart and a server quote.
2. "Place order" calls a Server Action with an idempotency key.
3. FastAPI locks the cart, re-checks prices and stock, reserves inventory,
   copies address and lines into the order, empties the cart, commits.
4. Staff move the order through the state machine in `/admin/orders`;
   delivery converts the reservation, cancellation releases it, exactly once.

## Deliberately not used

Microservices, Kubernetes, Redis, message queues, Elasticsearch, WebSockets,
external AI APIs, payment and courier integrations. See the README's
"Known limitations" and "Future work".

## Future external services (not implemented)

| Service | Purpose |
| --- | --- |
| Object storage | Admin photo uploads and return evidence photos |
| Payment providers | MTN MoMo, Orange Money, cards (today: manual demo states) |
| Courier APIs | Delivery quotes, tracking, return pickup |
| Notifications | Email/SMS/push for order, return and support updates |
| Shared rate limiting / observability | Needed when running several API workers |
