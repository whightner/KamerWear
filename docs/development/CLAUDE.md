# CLAUDE.md — instructions for coding agents

KamerWear is a fashion e-commerce platform for Cameroon, built as a two-week
school MVP. Simple, readable, demo-reliable code matters more than anything clever.

## Rules

1. **Read this document before modifying the repository.**
2. **Respect `docs/development/nextjs-AGENTS.md`.** The installed Next.js version may be newer than
   your training data. Read the docs under `frontend/node_modules/next/dist/docs/`
   before relying on any Next.js API.
3. **Prefer understandable code over clever abstractions.** No generic repository
   layers, DI frameworks or base classes "for later".
4. **Keep frontend and backend separated.** They communicate only through the REST API.
5. **Do not create microservices.** This is a modular monolith: one FastAPI app, one
   PostgreSQL database, one Next.js app. No Kubernetes, Redis, message queues or
   Elasticsearch.
6. **Never commit passwords, tokens, API keys or `.env` files.** Only `.env.example`
   files with placeholders are committed.
7. **All money amounts are stored as integers**, never floats.
8. **Currency for the MVP is XAF (FCFA).** XAF has no minor unit, so an integer
   amount is a whole number of francs (e.g. `15000` = 15 000 FCFA).
9. **Backend APIs live under `/api/v1`.**
10. **Keep modules ready for future mobile clients.** Business logic belongs in the
    API, not in the web frontend. Responses are plain JSON with no web-only
    assumptions.
11. **Do not implement features that are not in the current assigned task.**
12. **Every major feature must be testable independently.** Add tests with the feature.
13. **Preserve compatibility with the Figma-defined flows.**
    Design: https://www.figma.com/design/m6VMrJxXlWVUdAYCo3w3N8

## Where things go

```
frontend/                Next.js (App Router, TypeScript, Tailwind), code under src/
backend/app/
  api/v1/endpoints/      HTTP routes only: parse input, call a service, return a schema
  api/v1/router.py       registers every endpoint module
  core/config.py         settings from environment variables / backend/.env
  db/                    SQLAlchemy Base and session (get_db dependency)
  models/                SQLAlchemy models (import each one in models/__init__.py)
  schemas/               Pydantic request/response models
  services/              business logic, testable without HTTP
backend/alembic/         database migrations
backend/tests/           pytest tests
docs/                    architecture, API and database notes
```

## Working conventions

- Database schema changes always go through an Alembic migration
  (`alembic revision --autogenerate -m "..."`, then review the generated file).
- New settings go in `backend/app/core/config.py` and are documented in
  `backend/.env.example` with a placeholder value.
- Frontend reads the API base URL from `NEXT_PUBLIC_API_URL`.
- Catalog data comes only from the API through `frontend/src/lib/api/`. Never add
  a local product dataset or a mock fallback; show an error state instead.
- Keep files small and focused; split by feature when a file grows.

## Checks before finishing a task

```bash
# backend (from backend/, virtualenv active)
pytest

# frontend (from frontend/)
npm run lint
npm run build
```

Also confirm that no `.env`, `node_modules/`, `.next/`, `__pycache__/` or secrets are staged.
