# Security and privacy review (v1.0.0-demo)

A review of the academic demo MVP, done during the final QA task (Task 012).
It is not a professional penetration test or a production certification.

## Authentication

| Area | Implementation | Evidence |
| --- | --- | --- |
| Password hashing | Argon2id (argon2-cffi); long passphrases kept whole (no truncation) | `tests/test_auth.py` |
| Login | Identical answer for wrong password / unknown email; inactive accounts refused; failed logins rate-limited per email and per IP | `test_auth.py` |
| Access tokens | 15-minute HS256 JWT, signed with `JWT_SECRET_KEY` (required, ≥ 32 chars, placeholder refused); expired, forged and malformed tokens rejected; a refresh token can't be used as an access token | `test_auth.py`, `test_config.py` (weak or placeholder secret refused) |
| Refresh | 7-day single-use refresh tokens, rotated on every use; reusing an old one revokes the session | `test_refresh_rotates_tokens`, `test_reusing_an_old_refresh_token_revokes_the_session` |
| Logout | Revokes the session server-side immediately | `test_logout_revokes_session_immediately` |
| Password change | Signs out all other sessions | `test_change_password_success_signs_out_other_sessions` |
| Admin accounts | Created only by `python -m app.db.create_admin` (or the demo reset with environment values); public registration can't set role or flags | `test_public_registration_cannot_set_privileged_fields` |

## Web session, CSRF and redirects

- Tokens live only in **HttpOnly** cookies with **SameSite=Lax**, **Secure**
  in production builds (`AUTH_COOKIE_SECURE=false` exists only for trying a
  production build over plain http).
- Mutations are Server Actions (POST-only; Next.js checks the Origin).
  The cookie-authenticated POST route handlers (`/api/fit/estimate`, the two
  chat message routes) now also reject any request whose `Origin` isn't the
  site itself (**fixed in Task 012**, defence in depth on top of SameSite).
- Post-login redirects only accept same-site relative paths (`safeNextPath`
  rejects `//…`, backslashes and absolute URLs).
- CORS lists explicit origins; `*` is refused at startup because credentials
  are enabled.

## Authorization matrix

Verified server-side by `tests/test_authorization_matrix.py` (plus the
feature tests). Another customer's resource answers **404**, exactly like a
missing one, so references can't be probed.

| Check | Result |
| --- | --- |
| Customer A reads/edits B's profile | impossible: `/users/me` only returns the token's owner |
| A reads/edits/deletes B's address | 404 |
| A reads or tracks B's order (detail, timeline, return eligibility) | 404 |
| A reads or cancels B's return | 404 |
| A reads, polls, writes to or closes B's conversation | 404 |
| A changes B's cart lines | 404 |
| Customer on any of the 34 admin operations | 403 `admin_required` |
| Visitor on any admin operation | 401 |
| Customer posting as the store | impossible: the sender role comes from the endpoint |

Admin pages also check the role on the server before rendering; customers
see "Not authorized" and no admin data is fetched for them.

## Commerce integrity: values never trusted from the browser

| Value | Source of truth |
| --- | --- |
| Price, totals, discount | Catalog prices at order time, calculated by the API; quotes and orders reject client totals (`expected_total` only detects changes) |
| Delivery fee | Server rule by city (`services/delivery.py`) |
| Stock | Inventory rows locked at checkout; concurrent checkouts can't oversell (`test_checkout_concurrency.py`) |
| User id / owner | Access token only (`extra="forbid"` on inputs) |
| Payment success | Never accepted: payment states are manual admin records |
| Return quantity and value | Purchased minus active returns; purchase-time prices (`test_returns.py`) |
| Refund | Admin-recorded demo state; no provider call |
| Role | Database; never from input |

### Inventory and returns invariants

`python -m app.db.check_integrity` checks the live database (read-only):
`on_hand ≥ 0`, `reserved ≥ 0`, `on_hand ≥ reserved`, reserved equals the
units of open orders, order totals add up, histories end in the current
status, returned units ≤ purchased units, restock decisions and refund
amounts exist exactly when they should, and each return status is reached at
most once. All invariants held on the final demo database. Cancellation
releases stock once, delivery converts it once and return restocking happens
once; each is tested with concurrent requests
(`test_concurrent_cancellations_release_stock_once`,
`test_concurrent_receive_restocks_once`).

## XSS and output safety

- No `dangerouslySetInnerHTML`, `innerHTML` or `eval` anywhere in the
  frontend (searched). All user text (product descriptions, addresses,
  return notes, admin notes, support messages and subjects) renders as React
  text nodes, so markup shows as text.
- Support messages are stored exactly as typed; tests and the browser flow
  send `<script>alert(1)</script>` and `<img src=x onerror=…>` and check that
  they appear literally and no script runs.

## Files and images

| Path | Protections |
| --- | --- |
| Product image metadata | Admin can only reference `/images/products/<folder>/<file>.(webp|jpg|jpeg|png|avif)`; `..`, absolute paths and URLs refused; the index resolves files strictly inside the image root |
| Visual search upload | Uploads only (no URL fetching); ≤ 8 MB checked before parsing; JPEG/PNG/WebP by content; ≤ 8 000 px per side and 30 MP; decompression-bomb warnings treated as errors; decoded in memory, pixels copied (EXIF/GPS dropped); temporary spool file closed immediately; rate-limited |
| Smart Fit upload | Same loader and limits per photo; photos discarded after analysis; never written to disk, database or logs; only derived numbers kept (last 3 estimates) |
| Admin product photos / return evidence | No uploads exist (planned with object storage) |

## Privacy: personal data stored

| Data | Where | Notes |
| --- | --- | --- |
| Email, password hash, role | `users` | Argon2id hash only |
| First/last name, phone | `user_profiles` | phone optional |
| Sessions | `auth_sessions` | refresh-token id and times; **no IP address or user agent** |
| Delivery addresses | `addresses`, copied into `orders` | needed for delivery |
| Orders | `orders`, `order_items`, histories | purchase-time snapshots |
| Returns | `return_requests`, items, history | customer notes; staff internal notes |
| Support conversations | `support_conversations`, `support_messages` | plain-text messages |
| Confirmed Fit Profile | `fit_profiles` | sizes, height, preference; estimated dimensions only if confirmed from photos; deletable without deleting the account |
| Recent Smart Fit estimates | `fit_estimates` | derived numbers, last 3, deleted with the profile |

### Intentionally not retained

Visual search query photos, Smart Fit body photos, pose landmarks and
segmentation masks, EXIF/GPS metadata, card numbers, CVV, Mobile Money PINs or
any payment credentials (no payment provider is connected). Favorites are
kept in the page's memory for the current visit only and never reach the
server.

## Secrets

- Tracked files contain no passwords, JWT secrets, API keys or credentialed
  database URLs (searched; `.env.example` files hold `CHANGE_ME`
  placeholders, which the backend and the demo reset refuse).
- `backend/.env`, `frontend/.env.local`, model caches and build output are
  git-ignored.
- Test suites use throwaway passwords inside test code only.

## Dependency audit (2026-10-04)

| Tool | Scope | Result |
| --- | --- | --- |
| `pip-audit` | `requirements.txt`, `requirements-smart-fit.txt`, `requirements-visual-search.txt`, installed environment | No known vulnerabilities |
| `npm audit --omit=dev` | runtime packages (next, react, react-dom, lucide-react) | 0 vulnerabilities |
| `npm audit` (all) | includes dev tools | 5 "high": one advisory (`braces` stack-exhaustion DoS, GHSA-vfj7-8cjw-p6xm) through `eslint-config-next → @next/eslint-plugin-next → fast-glob → micromatch → braces`. **Development-only** (linting), not shipped or run in production. The suggested `npm audit fix --force` would downgrade `eslint-config-next` to 14.x (breaking); not applied |

Test tools (`pytest`, `httpx2`, `ruff`) moved from `requirements.txt` to
`requirements-dev.txt` in Task 012.

## Known residual risks (accepted for the demo)

- Rate limits and the refresh-coordination map are in memory, per process.
- The Origin check trusts the `Host`/`X-Forwarded-Host` header; a production
  deployment behind a proxy must forward the host correctly.
- No email verification, password reset or 2FA.
- No audit logging beyond order/return/payment histories.
- Real-world accuracy of Smart Fit is unvalidated; the real OpenCLIP weights
  are unvalidated (see the feature docs).
