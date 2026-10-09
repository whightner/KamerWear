# Security Policy

## Supported version

KamerWear is currently an **academic/demo MVP**. Security fixes target the latest code on `main` and the `v1.0.0-demo` code line where practical.

This repository is not a production-certified payment or healthcare system.

## Reporting a vulnerability

Please **do not open a public GitHub issue** for a vulnerability that could expose accounts, personal data, secrets, authorization boundaries or remote-code/file access.

Preferred reporting path:

1. Use GitHub's private vulnerability-reporting / Security Advisory feature for this repository if it is available.
2. If private reporting is not enabled, contact the repository owner privately through the GitHub account associated with this repository before publishing details.

Include:

- affected route/component;
- reproduction steps;
- expected vs actual behavior;
- impact;
- version/commit;
- proof-of-concept details only as necessary.

Do not include real user credentials or private customer data.

## Security scope

High-priority areas include:

- authentication and session handling;
- admin authorization;
- cross-customer data access;
- order/price/stock integrity;
- file upload and path traversal;
- XSS/injection;
- Smart Fit and Visual Search image handling;
- secrets/configuration exposure.

## Existing safeguards

The demo implements, among other controls:

- Argon2id password hashing;
- short-lived access tokens and rotating refresh sessions;
- HttpOnly/SameSite browser cookies;
- request-origin checks for cookie-authenticated mutations;
- owner checks on customer resources;
- ADMIN checks on admin endpoints;
- server-authoritative pricing, stock, totals and fees;
- content/dimension checks on AI image uploads;
- EXIF removal and non-retention of customer AI query/body photos.

See [docs/security-privacy.md](docs/security-privacy.md) for the full release review.

## Secrets

Never commit:

- `.env` files;
- PostgreSQL passwords;
- JWT signing keys;
- admin/customer passwords;
- model-provider tokens;
- private API keys.

If a secret is accidentally committed, rotate it immediately; deleting it from the newest commit is not sufficient.

## Disclosure

Please allow reasonable time for investigation and remediation before public disclosure.
