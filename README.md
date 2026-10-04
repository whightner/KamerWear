# KamerWear

**KamerWear v1.0.0-demo** is an academic/demo MVP of a fashion e-commerce
platform for Cameroon: shoes, clothes and accessories, priced in **XAF (FCFA)**,
with delivery to Cameroonian cities, an admin back office and two AI-assisted
features (visual search and Smart Fit). It was built in two weeks as a school
project. The code favours clarity and reliability over cleverness. It is not a
production-certified shop: payments and couriers are simulated.

## The problem

Online fashion shoppers in Cameroon often can't try items on, describe what
they want in words, or easily follow and return orders. KamerWear explores:

- **finding products from a photo** (visual search), instead of guessing keywords;
- **estimating a clothing size** from the customer's height and two guided
  photos (Smart Fit), always confirmed by the customer;
- a complete, trustworthy order flow: server-calculated totals, tracking,
  returns and support conversations;
- a simple back office for a small store team.

## Features

| Customers | Store staff (`/admin`) |
| --- | --- |
| Registration, login, profile, password change | Dashboard (orders, stock, returns and support badges) |
| Delivery addresses across Cameroon | Products, categories, variants, image metadata |
| Catalog with search, filters, sorting | Inventory (on-hand stock; reserved is order-controlled) |
| Product pages with colour/size variants and live stock | Order fulfilment with a strict state machine |
| Favorites (current visit) | Manual (demo) payment states |
| Cart saved to the account; guest cart merged at login | Returns: approve/reject, receive with per-item restock, demo refund |
| Checkout with server-calculated delivery fee and total | Support conversations with customers |
| Order history and tracking timeline | Visual search index status and rebuild |
| **Visual search** by photo and "Find Similar" | |
| **Smart Fit** size recommendations (review and confirm) | |
| Returns within 7 days of delivery | |
| Support conversations (optionally about an order/return) | |

Screenshots of the clean demo data are in [docs/screenshots/](docs/screenshots/).

## Architecture

A **modular monolith**: one Next.js web app, one FastAPI API, one PostgreSQL
database; the pretrained AI models run inside the API process.

```
Browser ──► Next.js (pages, Server Actions, small BFF) ──REST /api/v1──► FastAPI
                                                                   ├── PostgreSQL 18
                                                                   ├── OpenCLIP ViT-B-32  (visual search)
                                                                   └── MediaPipe Pose     (Smart Fit)
```

The browser only talks to Next.js; tokens stay in HttpOnly cookies; all
business rules (prices, stock, eligibility, sizes) live in the API, so a future
mobile app could reuse it.

| Document | Content |
| --- | --- |
| [docs/architecture/overview.md](docs/architecture/overview.md) | Final architecture, modules, request flow |
| [docs/architecture/](docs/architecture/) | Auth, commerce, admin, visual search, Smart Fit, returns & support |
| [docs/database/er.md](docs/database/er.md) | Entity–relationship overview (24 tables) |
| [docs/api/inventory.md](docs/api/inventory.md) | Endpoint inventory; details in [docs/api/README.md](docs/api/README.md) |
| [docs/security-privacy.md](docs/security-privacy.md) | Security review, authorization matrix, data inventory, audits |
| [docs/demo/README.md](docs/demo/README.md) | Demo preparation, startup, health check, recovery, demo paths |
| [docs/qa-report.md](docs/qa-report.md) | Final QA results (tests, accessibility, performance, validation status) |
| [docs/release-notes.md](docs/release-notes.md) | v1.0.0-demo release notes |

## Stack

- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4, ESLint
- **Backend**: Python 3.14 (3.11+ should work; developed and tested on 3.14.8),
  FastAPI, Uvicorn, Pydantic 2, SQLAlchemy 2, psycopg 3, Alembic, Argon2id, PyJWT
- **Database**: PostgreSQL 18 (tested on 18.4)
- **AI (optional)**: open_clip + PyTorch (visual search), MediaPipe (Smart Fit)
- **Tests**: pytest, ruff; Playwright + axe-core were used for browser checks

## Setup from zero

Prerequisites: Git, Python 3.11+ (3.14 tested), PostgreSQL 18, Node.js 20.9+
with npm.

### 1. Clone and create the database

```bash
git clone <repository-url> KamerWear && cd KamerWear
psql -U postgres -c "CREATE DATABASE kamerwear;"
```

### 2. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate                # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt          # add requirements-dev.txt for tests and lint
cp .env.example .env                     # Windows: copy .env.example .env
```

Edit `backend/.env`: put your PostgreSQL password in `DATABASE_URL` and a
random `JWT_SECRET_KEY`
(`python -c "import secrets; print(secrets.token_urlsafe(48))"`). Placeholders
are refused at startup.

```bash
alembic upgrade head                     # create all tables
```

Then either load the **demo presentation data** (recommended; deletes users and
orders, see [docs/demo/README.md](docs/demo/README.md)):

```bash
export DEMO_ADMIN_EMAIL=... DEMO_ADMIN_PASSWORD=...            # your choice, ≥ 10 characters
export DEMO_CUSTOMER_EMAIL=... DEMO_CUSTOMER_PASSWORD=...
python -m app.db.reset_demo --yes
```

or only the catalog, plus an admin you type in:

```bash
python -m app.db.seed
python -m app.db.create_admin
```

Start the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API docs: http://localhost:8000/docs · health: http://localhost:8000/api/v1/health

### 3. Frontend

```bash
cd frontend
npm ci
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > .env.local
npm run build && npm run start           # production build on http://localhost:3000
# or for development: npm run dev
```

Open **http://localhost:3000** (use `localhost`: auth cookies are Secure in
production builds, which browsers allow on localhost).

### 4. AI models (optional, internet needed once)

```bash
cd backend
pip install -r requirements-smart-fit.txt       # Linux: sudo apt-get install libegl1 libgles2
python -m app.ai.prepare_smart_fit              # 30 MB, SHA-256 verified, self-test
pip install -r requirements-visual-search.txt   # PyTorch + open_clip
python -m app.ai.prepare_visual_search          # ~600 MB from Hugging Face, self-test
python -m app.ai.visual_search_index            # encode the catalog photos

# before a presentation, verify without network:
python -m app.ai.prepare_smart_fit --offline
python -m app.ai.prepare_visual_search --offline   # then set VISUAL_SEARCH_OFFLINE=true
```

Without them the shop works normally; the two features say they are
unavailable and never show fake results.

### 5. Check everything

```bash
cd backend
python -m app.demo.healthcheck          # database, API, web, logins, visual index, Smart Fit model
python -m app.db.check_integrity        # inventory/order/return/support invariants
```

## Testing

```bash
cd backend && pip install -r requirements-dev.txt
pytest                                  # uses a separate kamerwear_test database (created automatically)
ruff check app tests          # settings in backend/ruff.toml

cd frontend
npm run lint
npm run build
```

Database tests are skipped if PostgreSQL isn't reachable. Optional tests for
the real models skip when their packages or weights are missing. Final
results are in [docs/qa-report.md](docs/qa-report.md).

## Security and privacy highlights

- Argon2id passwords; short-lived JWTs; single-use rotating refresh tokens
  with reuse detection; logout and password change revoke sessions.
- Tokens only in HttpOnly SameSite=Lax cookies; Server Actions and the
  cookie-authenticated route handlers check the request origin.
- Every resource is owner-checked by the API (another customer's order,
  return or conversation answers 404); all admin routes require the ADMIN role.
- Prices, totals, fees, stock, refunds and roles are never accepted from the
  browser.
- No raw HTML is rendered; uploads are validated by content, size and
  dimensions, decoded in memory, stripped of EXIF and never stored.
- Stored personal data: account, profile, addresses, orders, returns, support
  messages, confirmed Fit Profile. Not stored: search photos, body photos,
  payment card data or PINs.

Details: [docs/security-privacy.md](docs/security-privacy.md).

## Known limitations

- **Payments are simulated**: Mobile Money, card and cash on delivery are demo
  choices; payment and refund states are recorded manually by staff.
- **No courier integration**: delivery fees are a flat demo rule per city;
  statuses are updated by staff; no return pickup.
- **Visual search real-weight validation is pending**: the pretrained
  OpenCLIP weights could not be downloaded in the development environment
  (Hugging Face blocked), so result quality with the real model is unverified;
  thresholds are untuned.
- **Smart Fit accuracy is unvalidated**: the real pose model runs, but no
  comparison with tape measurements on consenting volunteers has been made.
  Estimates are sensitive to clothing, pose and framing; front-only estimates
  are always low confidence.
- **Generic demo size charts**, the same for every product; shoe sizes are
  entered by the customer.
- **Support uses polling** (every 4 s on an open conversation), not push; no
  email/SMS/push notifications.
- **Process-local state**: rate limits and session-refresh coordination live in
  one API/Next.js process.
- **No uploads**: admin product photos are existing static files (metadata
  only); returns have no photo evidence; chat is text-only.
- **Favorites** last for the current visit only.
- No password reset, email verification, promotions engine, reviews, or native
  mobile app.
- Accessibility was checked with automated tools (axe) and keyboard tests;
  no screen-reader user testing. Browser automation covered Chromium only.

## Future work

- MTN MoMo / Orange Money and card payment integrations (with real refunds)
- Courier APIs for delivery quotes, tracking and return pickup
- Validating Smart Fit with measured volunteers; brand-specific size charts
- Object storage for admin photo uploads and return evidence
- Email/SMS/push notifications
- Shared rate limiting and production observability for several workers
- A native mobile app on the same API

## Project rules

See [CLAUDE.md](CLAUDE.md) (coding rules) and the Figma design:
https://www.figma.com/design/m6VMrJxXlWVUdAYCo3w3N8
