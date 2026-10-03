# KamerWear

KamerWear is a fashion e-commerce platform, starting with Cameroon. It sells
shoes, clothes, streetwear, accessories and other wearable fashion products.
Prices are in **XAF (FCFA)**.

This repository is a school/project MVP with a demo scheduled about two weeks
after project start. The code favours clarity and reliability over cleverness.

## Product scope

The product is built task by task. The roadmap includes:

- product browsing, categories and search
- visual/camera search and "find similar" from an image
- favorites, shopping cart and checkout
- Cameroon delivery addresses and order tracking
- customer/store chat, returns and refunds
- promotions and flash deals
- customer Fit Profile with AI-assisted size recommendation
- admin dashboard

UI direction comes from the Figma file:
https://www.figma.com/design/m6VMrJxXlWVUdAYCo3w3N8
(V2 product board: `node-id=12-2`, developer handoff: `node-id=12-718`).

### Current scope

The storefront reads a real catalog from the API. Customers can create an
account, save delivery addresses, keep a cart in their account, check out with
a demo payment method, and follow their orders with status tracking. Real
payments, couriers and the AI features are not built yet; see
[Project status](#project-status).

## Architecture

A **modular monolith**: one web frontend, one API, one database.

```
Browser
   ↓
Next.js / React        (frontend/)
   ↓  REST + JSON over HTTP
FastAPI                (backend/)
   ↓  SQLAlchemy
PostgreSQL
```

The frontend never talks to the database. All business rules live in the API, so a future mobile
app can reuse the same endpoints. See
[docs/architecture/overview.md](docs/architecture/overview.md) for details and
for the external services planned for later.

### Frontend stack

- Next.js (App Router) with React
- TypeScript
- Tailwind CSS
- ESLint
- Source code under `frontend/src/`

### Backend stack

- Python 3.11+ (developed with 3.14)
- FastAPI, served by Uvicorn
- Pydantic and pydantic-settings for validation and configuration
- SQLAlchemy 2.x ORM with the psycopg 3 PostgreSQL driver
- Alembic for database migrations
- pytest for tests

## Project structure

```
KamerWear/
├── frontend/                 Next.js app (see frontend/AGENTS.md)
├── backend/
│   ├── app/
│   │   ├── api/v1/           REST endpoints, mounted under /api/v1
│   │   ├── db/               SQLAlchemy base and session
│   │   ├── core/             settings, password hashing/JWT, rate limiting
│   │   ├── models/           database models (catalog, users, addresses, carts, orders)
│   │   ├── schemas/          request/response models
│   │   ├── services/         business logic (catalog, auth, cart, orders, delivery fees)
│   │   └── main.py           FastAPI application
│   ├── alembic/              migrations
│   ├── tests/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env.example
├── docs/
│   ├── architecture/
│   ├── api/
│   └── database/
├── .env.example              which env file each app uses
├── CLAUDE.md                 rules for coding agents
└── README.md
```

## Development setup

Prerequisites: Python 3.11+, PostgreSQL 16+ (tested on 16 and 18), Node.js 20.9+ and npm, Git.

The storefront needs **both services running**: product data comes from the
FastAPI catalog API, which reads PostgreSQL. Without the API the storefront
shows a "couldn't load the catalog" message (there is no offline product copy).

### 1. Database

Create an empty database named `kamerwear`:

```bash
psql -U postgres -c "CREATE DATABASE kamerwear;"
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Activate the virtualenv
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell

pip install -r requirements.txt

# Configure: copy the example, then put your PostgreSQL password in DATABASE_URL
# and a random JWT_SECRET_KEY (see the comment in the file for a command).
cp .env.example .env               # Windows: copy .env.example .env

alembic upgrade head               # create the catalog, account and order tables
python -m app.db.seed              # load the demo catalog (safe to run again)
uvicorn app.main:app --reload      # http://localhost:8000
```

Optional: create an admin account (prompts for the details; nothing is
hard-coded, and the seed never creates users):

```bash
python -m app.db.create_admin
```

Optional: move a demo order along the tracking timeline (there is no admin
dashboard yet):

```bash
python -m app.db.set_order_status KW-2026-7K4M9Q shipped --note "Left the Douala hub"
```

Useful URLs:

- http://localhost:8000/ is the API identification
- http://localhost:8000/api/v1/health is the health check
- http://localhost:8000/docs is the interactive API documentation
- http://localhost:8000/api/v1/products lists the demo catalog

Run the tests. Catalog tests use a separate `kamerwear_test` database (created
automatically) and are skipped if PostgreSQL is not running:

```bash
pytest
```

### 3. Frontend

In a second terminal (keep the backend running):

```bash
cd frontend
npm install
```

Create `frontend/.env.local` (next to `package.json`):

```
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Then:

```bash
npm run dev      # http://localhost:3000
npm run lint
npm run build
```

### Day-to-day

| Terminal | Command |
| --- | --- |
| A — API | `cd backend` → activate the virtualenv → `uvicorn app.main:app --reload` |
| B — web | `cd frontend` → `npm run dev` |

After changing the seed data, run `python -m app.db.seed` again; the
storefront always fetches fresh data.

## How the frontend and backend communicate

- The frontend calls the backend over HTTP using JSON, at the base URL in
  `NEXT_PUBLIC_API_URL` (e.g. `http://localhost:8000/api/v1`).
- Catalog requests are made by the Next.js server while rendering pages
  (`frontend/src/lib/api/catalog.ts`, always fresh: `cache: "no-store"`), so the
  browser only talks to the Next.js app. Product images are static files served
  by Next.js from `frontend/public/images`; the API stores only their paths.
- `/shop` keeps filters, search, sorting and page in the URL and passes them to
  `GET /api/v1/products`; the API does all filtering.
- Every backend endpoint is versioned under `/api/v1`.
- The backend allows browser requests only from the origins listed in
  `CORS_ORIGINS` (default `http://localhost:3000`). Wildcard `*` is rejected.
- Money is exchanged as integers in XAF (e.g. `15000` means 15 000 FCFA).
- Accounts: login, registration and the account pages use Next.js Server
  Actions that call `/api/v1/auth/*` and `/api/v1/users/me`. Tokens are kept
  in HttpOnly cookies on the Next.js site and sent to FastAPI as a Bearer
  header; browser JavaScript never sees them. `/account` and
  `/account/profile` require a session. Details, including CSRF and token
  refresh: [docs/architecture/auth.md](docs/architecture/auth.md).
- Cart and checkout: a signed-in customer's cart is saved in PostgreSQL; a
  guest's cart lives in browser memory and is merged into the account at
  login (checkout requires an account). FastAPI calculates every price, the
  delivery fee (demo rule: Douala 1 500, Yaoundé 2 000, Bafoussam 2 500, other
  cities 3 500 FCFA) and the total, re-checks stock with row locks and reserves
  it when the order is placed. Mobile Money, Card and Cash on Delivery are
  **demo** methods: no payment is taken and no card or PIN is ever requested.
  Details: [docs/architecture/commerce.md](docs/architecture/commerce.md).

## Project status

| Area | Status |
| --- | --- |
| Repository structure and docs | Done (Task 001) |
| Backend skeleton, health endpoint, CORS | Done (Task 001) |
| Database connection and Alembic setup | Done (Task 001), no tables yet |
| Desktop storefront homepage (mock data) | Done (Task 002) |
| Catalog, product pages, frontend cart and favorites (mock data) | Done (Task 003) |
| Catalog database, seed and REST API (`/api/v1/products`, `/categories`) | Done (Task 004) |
| Storefront reads the catalog API (no frontend mock catalog) | Done (Task 005) |
| Customer accounts: register, login, logout, profile, password change | Done (Task 006) |
| Addresses, saved cart, checkout (demo payments), orders and status tracking | Done (Task 007) |
| Real payments, courier integration, admin dashboard, saved favorites, returns, AI features | Not started (future tasks) |
