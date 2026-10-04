# Demo guide (presentation checklist)

How to prepare, run, check and recover the KamerWear demo. Everything runs
locally: PostgreSQL, the FastAPI API and the production build of the Next.js
site. Nothing needs the internet during the presentation once the models are
prepared.

## 1. The day before

```bash
# Backend (from backend/, virtualenv active)
pip install -r requirements.txt
pip install -r requirements-smart-fit.txt          # MediaPipe (+ libegl1 libgles2 on Linux)
pip install -r requirements-visual-search.txt      # OpenCLIP + torch (large)
python -m app.ai.prepare_smart_fit                 # downloads 30 MB, verifies, self-test
python -m app.ai.prepare_visual_search             # downloads ~600 MB from Hugging Face, self-test

# Frontend (from frontend/)
npm ci
npm run build                                      # NEXT_PUBLIC_API_URL must be set (frontend/.env.local)
```

Then check offline readiness (no network used):

```bash
python -m app.ai.prepare_smart_fit --offline       # must print "Ready"
python -m app.ai.prepare_visual_search --offline   # must print "Ready"
```

Set `VISUAL_SEARCH_OFFLINE=true` in `backend/.env` so the API never tries to
download weights.

> Status at release: Smart Fit's model was prepared and ran in the development
> environment. The OpenCLIP weights could **not** be downloaded there
> (huggingface.co blocked by the network policy), so the visual-search model
> has not yet been run with real weights. Prepare it on the presentation
> laptop with internet access, then run
> `python -m app.ai.evaluate_visual_search` once to see real results.

## 2. Accounts

Choose credentials on the presentation laptop only (never commit them):

```bash
export DEMO_ADMIN_EMAIL=...        DEMO_ADMIN_PASSWORD=...      # ≥ 10 characters
export DEMO_CUSTOMER_EMAIL=...     DEMO_CUSTOMER_PASSWORD=...
```

(or put them in `backend/.env`; see `backend/.env.example`). An extra admin can
always be created with `python -m app.db.create_admin`.

## 3. Reset to the presentation state (morning of the demo)

```bash
cd backend
python -m app.db.reset_demo --yes
python -m app.ai.visual_search_index      # only if the reset says the model wasn't available
python -m app.db.check_integrity          # optional: "All invariants hold."
```

The reset refuses to run without `--yes`, on a non-local database host or when
`APP_ENV`/`ENVIRONMENT` is `production`. It deletes all users and orders,
reloads the catalog and creates:

| What | Details |
| --- | --- |
| Accounts | the admin and customer from `DEMO_*` (customer "Amina Ndongo"); "Brice Mbarga" and "Clarisse Fotso" are fictional customers without a usable login |
| Stock | most variants 8–24 units; 5 low-stock variants (e.g. Canvas Messenger Bag, Classic Hoodie XL olive "Only 1 left"); 3 sold-out sizes (Urban Runner 02 size 45, Core Heavy Tee XXL black, Everyday Cargo 36 royal blue) |
| Amina's orders | **Confirmed** (Classic Hoodie + Core Joggers), **Shipped** (Urban Runner 02), **Delivered, return-eligible** (Core Heavy Tee ×2 + Everyday Cargo), **Delivered + requested return** (Trail Zip Jacket, wrong size) |
| Other orders | Brice: delivered, return **refunded (demo)**; Clarisse: **new, awaiting confirmation** |
| Support | Amina ↔ store about the shipped order (open, last customer message unread by staff); Brice's refund question (closed) |

Run it on the presentation day: the 7-day return window counts from the
delivery times it creates (2–5 days in the past).

## 4. Start the demo (production build)

```bash
# Terminal 1: PostgreSQL must be running, then
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend && npm run start          # serves the build on http://localhost:3000
```

Open **http://localhost:3000** (use `localhost`, not another host name: auth
cookies are Secure in production builds, and browsers allow that on localhost).

## 5. Health check

```bash
cd backend && python -m app.demo.healthcheck
```

Expected:

```
✓ Database: PostgreSQL 18.x, 19 active products
✓ API /health: 200 ok
✓ Next.js reachable: 200
✓ Admin login: … (admin)
✓ Customer login: … (customer)
✓ Visual search index: 69/69 photos indexed, model ViT-B-32/laion2b_s34b_b79k
✓ Smart Fit model: pose_landmarker_heavy.task present, mediapipe importable
Ready for the demo.
```

## 6. Demo paths

### Customer (≈ 6 minutes)

1. **Home** → "Popular picks", flash deals, Smart Fit and visual search banners.
2. **Shop** → filter Clothing + Men, sort by price; search "hoodie".
3. **Product** Classic Hoodie → colours/sizes, "Only 1 left" on XL olive,
   Smart Fit block ("Log in to see…" / recommended size once logged in).
4. **Log in** as the demo customer → **Smart Fit** (`/fit`), see below.
5. Back on the product → "Recommended size for you: M" → **Select recommended size** → **Add to cart**.
6. **Cart → Checkout** → saved address, delivery fee for Douala, Cash on delivery → **Place order**.
7. **Orders** → the new order's timeline; open the **Shipped** order → tracking.
8. **Contact support** from the shipped order, or open the existing conversation in **Support**.
9. Open the **Delivered** order → **Request a return** → choose the tee, 1 unit,
   "Wrong size" → review → submit → status **Requested**.

### Admin (≈ 4 minutes)

1. **Dashboard** → open orders, low stock, returns and support badges.
2. **Products** → open a product, edit the price or a variant's stock.
3. **Inventory** → low-stock filter.
4. **Orders** → Clarisse's new order → Confirm → Preparing → Shipped →
   Out for delivery → Delivered (stock moves exactly once); note the demo payment state.
5. **Returns** → Amina's Trail Zip Jacket return → Approve → Mark received
   (Restockable) → Record demo refund ("no payment provider" notice);
   compare with Brice's completed return.
6. **Support** → reply to Amina; her open page shows the reply within ~4 s.

### Visual search

Use a local photo, never a download during the defense. A safe choice is a
catalog photo copied to the laptop beforehand, e.g.
`frontend/public/images/products/urban-runner-02/black-1.webp` (a sneaker) or
`classic-hoodie/olive-1.webp`. **Search by image** → upload → results with
the predicted type; then "Find Similar" on a product page. Explain that scores
are similarities for ranking, not accuracy.

### Smart Fit

- **Live**: logged in as the customer, `/fit` → height → front photo (full
  body, arms slightly away, good light) → side photo → review → correct →
  save → product recommendation.
- **Backup**: if lighting or framing makes the capture fail, show the
  screenshots in `docs/screenshots/` (review step, account Fit Profile, product
  recommendation) and enter sizes manually on `/account/fit-profile`. The
  release contains no body photos of real people.

## 7. Recovery plan

| Problem | Do this |
| --- | --- |
| Database broken / messy after rehearsals | `python -m app.db.reset_demo --yes` (then rebuild the visual index if prompted) |
| PostgreSQL not running | start the PostgreSQL service, then re-run the health check |
| API crashed | restart Terminal 1 (`uvicorn app.main:app --host 127.0.0.1 --port 8000`) |
| Frontend crashed | restart Terminal 2 (`npm run start`; rebuild only if code changed) |
| Logged out unexpectedly | log in again (sessions last 7 days; logging in elsewhere doesn't log you out) |
| Visual search unavailable | the page shows "Visual search is unavailable"; show `docs/screenshots/` and explain that the pretrained weights must be prepared locally (the model host was blocked during development) |
| Smart Fit capture fails | explain the guided-photo sensitivity (light, full body, arms away), show the screenshots, enter sizes manually |
| Too many requests (429) | wait a minute (in-memory rate limits) or restart the API |

## 8. Final screenshots

`docs/screenshots/` holds presentation screenshots taken from the clean demo
data at 1440 × 900 (full page). Retake them after any visual change.
