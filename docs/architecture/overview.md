# Architecture overview

KamerWear is a **modular monolith**. A single Next.js web app talks to a single
FastAPI application, which owns a single PostgreSQL database. This is the
simplest architecture that supports the MVP, and it is easy to run locally for a demo.

```
Browser
   ↓
Next.js / React
   ↓
REST API  (JSON over HTTP, /api/v1)
   ↓
FastAPI
   ↓
PostgreSQL
```

## Layers

### Browser

Customers use KamerWear in a web browser, on a phone or a desktop. The UI follows the
Figma product board.

### Next.js / React (`frontend/`)

- Renders pages and handles UI state.
- Calls the backend REST API. It holds no business rules and never accesses the
  database directly.
- Reads the API base URL from `NEXT_PUBLIC_API_URL`.
- Holds the customer's auth tokens in HttpOnly cookies and forwards them to the
  API from the server; see [auth.md](auth.md).
- Shows carts, checkout totals and orders exactly as the API returns them; the
  API computes prices, fees, stock and totals. See [commerce.md](commerce.md).

### REST API

- JSON over HTTP, versioned under `/api/v1`.
- Is the only contract between clients and the backend. A future mobile app
  will use the same endpoints, so responses must not assume a web client.
- CORS restricts browser access to the configured frontend origins.
- See [../api/README.md](../api/README.md) for conventions.

### FastAPI (`backend/`)

The backend is one Python application, split into modules by responsibility:

| Package | Responsibility |
| --- | --- |
| `app/api/v1/endpoints/` | HTTP routes: validate input, call services, return schemas |
| `app/schemas/` | Pydantic request/response models (the API contract) |
| `app/services/` | Business logic, testable without HTTP |
| `app/models/` | SQLAlchemy models (database tables) |
| `app/db/` | Declarative base and database sessions |
| `app/core/` | Configuration, password hashing and JWTs, rate limiting |

As features arrive (catalog, cart, orders, …), each one adds its own endpoint,
schema, service and model files. They stay inside this same application.

### PostgreSQL

- The single source of truth for all business data.
- Schema changes are managed by Alembic migrations in `backend/alembic/`.
- See [../database/README.md](../database/README.md) for conventions.

## Future external services (not implemented)

Several roadmap features will rely on outside services. None of them is part
of the current code. When one is added, the backend calls it from a small
service module in `app/services/`, and the frontend keeps talking only to the
KamerWear API.

| Service | Purpose |
| --- | --- |
| Image / object storage | Store product photos and customer-uploaded images (e.g. an S3-compatible bucket) |
| Visual-search engine | Camera search and "find similar" from an image |
| AI Fit service | Size recommendation based on the customer's Fit Profile |
| Payment provider | Mobile Money (MTN MoMo, Orange Money) and card payments |
| Delivery provider | Shipping quotes and parcel tracking within Cameroon |

```
                      ┌──────────────────────┐
                      │       FastAPI        │
                      └──────────┬───────────┘
        ┌──────────────┬─────────┼──────────┬──────────────┐
        ↓              ↓         ↓          ↓              ↓
   PostgreSQL    Object storage  Visual   AI Fit     Payment / delivery
                                 search   service    providers
                     (future)   (future)  (future)      (future)
```

## Deliberately out of scope

To keep the MVP small and reliable, the project does **not** use
microservices, Kubernetes, Redis, message brokers (RabbitMQ/Kafka) or
Elasticsearch. Search starts with PostgreSQL.
