# Contributing to KamerWear

Thanks for your interest in KamerWear.

KamerWear is an academic/demo MVP, so contributions should keep the codebase understandable, testable and appropriately scoped.

## Before you start

1. Read the main [README](README.md).
2. Review [docs/architecture/](docs/architecture/) for the subsystem you plan to change.
3. Check existing issues before creating a duplicate.
4. For security vulnerabilities, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.

## Local setup

Use the setup instructions in the README. Never commit:

- `.env` files
- passwords or database credentials
- JWT/API secrets
- downloaded model weights
- customer/private images
- local databases, logs or build artifacts

## Development expectations

- Keep the modular-monolith architecture unless there is a documented reason to change it.
- Keep business rules in FastAPI rather than trusting browser values.
- Store money as integer XAF/FCFA values.
- Preserve authorization and ownership checks.
- Do not label test/fallback behavior as AI.
- Keep Smart Fit and Visual Search limitations explicit.
- Prefer small, focused changes over unrelated refactors.

## Branches and commits

Create a short-lived branch from `main`.

Examples:

```text
feat/persistent-favorites
fix/order-stock-warning
docs/setup-windows
```

Use clear commit messages, for example:

```text
feat: add ...
fix: prevent ...
docs: clarify ...
test: cover ...
chore: ...
```

## Required checks

Backend changes:

```bash
cd backend
pytest
ruff check app tests
```

Frontend changes:

```bash
cd frontend
npm ci
npm run lint
npm run build
```

For UI changes, also check the affected page at desktop and mobile widths and avoid introducing accessibility regressions.

## Pull requests

A pull request should explain:

- what changed;
- why it changed;
- how it was tested;
- screenshots for meaningful UI changes;
- migrations/environment changes;
- known limitations or follow-up work.

Please keep pull requests focused.

## Third-party content

Do not add images, fonts, model weights, datasets or other assets without a clear license/permission. Update [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and the relevant credits file when necessary.

By contributing code to this repository, you agree that your contribution may be distributed under the repository's MIT License.
