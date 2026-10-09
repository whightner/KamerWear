# KamerWear

<p align="center">
  <strong>Intelligent fashion e-commerce for Cameroon</strong><br/>
  Catalog · Smart Fit · Visual Search · Orders · Returns · Support · Admin
</p>

<p align="center">
  <img alt="Demo" src="https://img.shields.io/badge/status-v1.0.0--demo-1f1f1f">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-f2b632">
  <img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-black">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-Python-009688">
  <img alt="PostgreSQL" src="https://img.shields.io/badge/PostgreSQL-18-336791">
</p>

> **Academic/demo MVP.** KamerWear is not a production-certified store. Payments, refunds and courier operations are simulated. Visual Search and Smart Fit are prototypes with documented limitations.

KamerWear is a full-stack fashion-commerce platform focused on clothing, shoes and accessories priced in **XAF (FCFA)**. It combines a complete shopping flow with store administration and two AI-assisted experiences: image-based product discovery and guided size recommendations.

## Preview

<p align="center">
  <img src="docs/screenshots/01-home.jpg" width="49%" alt="KamerWear storefront homepage">
  <img src="docs/screenshots/02-catalog.jpg" width="49%" alt="KamerWear product catalog">
</p>
<p align="center">
  <img src="docs/screenshots/03-product-smart-fit.jpg" width="49%" alt="Product page with Smart Fit">
  <img src="docs/screenshots/10-admin-dashboard.jpg" width="49%" alt="KamerWear admin dashboard">
</p>

More screenshots are available in [docs/screenshots/](docs/screenshots/).

## What problem does it explore?

Online fashion customers may struggle to describe an item they saw, choose a suitable size without trying it on, or follow after-sales processes consistently. KamerWear explores a locally oriented workflow with:

- **Visual Search** — upload/take a photo and search the catalog by image similarity.
- **Smart Fit** — guided photos + known height produce an estimated clothing-size recommendation that the customer reviews and confirms.
- **Commerce fundamentals** — catalog, variants, inventory, cart, checkout, orders, tracking, returns and support.
- **Store operations** — products, categories, stock, fulfilment, returns, support and visual-search indexing from an admin back office.

## Features

| Customer experience | Store administration |
| --- | --- |
| Registration, login and profile | Operational dashboard |
| Cameroon delivery addresses | Products, categories and variants |
| Search, filters and sorting | Product image metadata |
| Colour/size variants with live stock | Inventory and low-stock views |
| Persistent account cart + guest merge | Order fulfilment state machine |
| Server-calculated checkout | Manual **demo** payment states |
| Order history and tracking timeline | Return processing and restocking |
| Smart Fit recommendations | Customer support conversations |
| Visual Search / Find Similar | Visual-search index status/rebuild |
| Returns within the demo policy | Role-protected admin routes |
| Customer support conversations | |

## Architecture

KamerWear is intentionally a **modular monolith**: one web application, one API and one PostgreSQL database.

```text
Browser
  │
  ▼
Next.js 16 / React 19
  │  Server Actions / BFF
  ▼
FastAPI  /api/v1
  ├── PostgreSQL 18
  ├── OpenCLIP ViT-B-32   (optional Visual Search)
  └── MediaPipe Pose      (optional Smart Fit)
```

The browser does not receive raw auth tokens. Next.js stores access/refresh tokens in HttpOnly cookies and calls FastAPI. Business rules such as prices, stock, order ownership, return eligibility and admin authorization are enforced by the API.

## Technology stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS 4, ESLint
- **Backend:** Python, FastAPI, Pydantic 2, SQLAlchemy 2, psycopg 3, Alembic, Uvicorn
- **Auth:** Argon2id password hashing, PyJWT, rotating refresh sessions
- **Database:** PostgreSQL 18
- **AI (optional):** MediaPipe Pose; OpenCLIP + PyTorch
- **Quality:** pytest, ruff, Playwright-based browser flows, axe-core accessibility checks

## Quick start

### Prerequisites

- Git
- Python 3.11+ (developed/tested on Python 3.14)
- PostgreSQL 18
- Node.js 20.9+ and npm

### 1. Clone and create the database

```bash
git clone https://github.com/whightner/KamerWear.git
cd KamerWear
psql -U postgres -c "CREATE DATABASE kamerwear;"
```

### 2. Backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

pip install -r requirements.txt
```

Copy the environment template:

```powershell
Copy-Item .env.example .env
```

On macOS/Linux:

```bash
cp .env.example .env
```

Edit `backend/.env`. At minimum, configure:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_POSTGRES_PASSWORD@localhost:5432/kamerwear
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
```

Generate a JWT secret with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Apply migrations and seed the catalog:

```bash
alembic upgrade head
python -m app.db.seed
```

Start the API:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API documentation: **http://localhost:8000/docs**

### 3. Create an administrator

Public registration creates **CUSTOMER** accounts only. Admin accounts are intentionally created from the backend CLI.

From `backend/` with the virtual environment active:

```bash
python -m app.db.create_admin
```

Follow the prompts for the administrator name, email and password.

Then log in at **http://localhost:3000/login** and open:

**http://localhost:3000/admin**

> Never commit admin passwords, PostgreSQL passwords, JWT secrets, API keys or real `.env` files.

### 4. Frontend

In a second terminal:

```bash
cd frontend
npm ci
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
```

Start development:

```bash
npm run dev
```

or verify/run the production build:

```bash
npm run build
npm run start
```

Open **http://localhost:3000**.

## Presentation/demo dataset

A guarded reset command can build a deterministic presentation dataset:

```bash
cd backend
python -m app.db.reset_demo --yes
```

Demo credentials come from `DEMO_*` environment variables and are **never hardcoded**. The reset command refuses unsafe environments. See [docs/demo/README.md](docs/demo/README.md) before using it.

## Optional AI setup

### Smart Fit

```bash
cd backend
pip install -r requirements-smart-fit.txt
python -m app.ai.prepare_smart_fit
python -m app.ai.prepare_smart_fit --offline
```

Smart Fit uses a pretrained MediaPipe Pose model. Customer body photos are processed temporarily and are not stored.

### Visual Search

```bash
cd backend
pip install -r requirements-visual-search.txt
python -m app.ai.prepare_visual_search
python -m app.ai.visual_search_index
python -m app.ai.prepare_visual_search --offline
```

Visual Search uses OpenCLIP embeddings. The real OpenCLIP weights could not be validated in the original cloud development environment because the model host was blocked, so real-weight search quality remains an explicit validation item.

Without optional AI dependencies, the rest of KamerWear continues to work and the unavailable AI feature reports that state instead of showing fake results.

## Testing

Backend:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
ruff check app tests
```

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

The final demo release recorded **543 passing backend tests, 0 failures and 1 optional OpenCLIP skip**, plus extensive Chromium browser-flow, responsive and automated accessibility checks. See [docs/qa-report.md](docs/qa-report.md) for the exact release evidence and limitations.

## Security & privacy highlights

- Argon2id password hashing.
- Short-lived access JWTs and rotating single-use refresh tokens backed by revocable sessions.
- HttpOnly, SameSite cookies for browser authentication.
- Server-side ownership checks for addresses, carts, orders, returns and support conversations.
- ADMIN authorization is enforced by FastAPI, not only by the UI.
- Prices, totals, stock, delivery fees and roles are recalculated/validated server-side.
- Uploaded AI images are validated by content and dimensions, stripped of EXIF and not retained.
- No card numbers, CVVs or Mobile Money PINs are requested or stored.

Read the full review in [docs/security-privacy.md](docs/security-privacy.md). Security reports should follow [SECURITY.md](SECURITY.md).

## Documentation

| Document | Purpose |
| --- | --- |
| [Architecture overview](docs/architecture/overview.md) | Final system/module architecture |
| [Architecture docs](docs/architecture/) | Auth, commerce, Smart Fit, Visual Search, returns/support |
| [ER overview](docs/database/er.md) | Main entities and relationships |
| [API inventory](docs/api/inventory.md) | Endpoint inventory |
| [Demo guide](docs/demo/README.md) | Reset, startup, health check, recovery |
| [QA report](docs/qa-report.md) | Release tests, accessibility, performance |
| [Release notes](docs/release-notes.md) | v1.0.0-demo notes |
| [Development guidelines](docs/development/) | Project/agent development notes |

## Known limitations

- Payments and refunds are simulated/manual; no real payment gateway is connected.
- No courier API or live GPS delivery tracking.
- OpenCLIP real-weight search quality still requires real-model validation.
- Smart Fit real-world measurement accuracy has not been validated against tape-measure ground truth.
- Generic demo size charts are used instead of brand-specific charts.
- Support uses lightweight polling rather than push/WebSockets.
- Process-local rate limits/refresh coordination assume a single process.
- Product/admin uploads and return-photo evidence need a production object-storage layer.
- Favorites are session/current-visit only.
- Automated browser QA covered Chromium; no formal screen-reader user study was performed.

## Contributing

Contributions are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) when participating in the project.

For vulnerabilities, **do not open a public issue**; follow [SECURITY.md](SECURITY.md).

## License

KamerWear's original source code is released under the [MIT License](LICENSE).

Third-party libraries, model weights and bundled demo imagery keep their own licenses/terms. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [frontend/public/images/CREDITS.md](frontend/public/images/CREDITS.md).

---

**KamerWear v1.0.0-demo** — academic/demo software, not production certification.
