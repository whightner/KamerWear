# KamerWear v1.0.0-demo — final QA report

Final quality, security and demo-readiness review (Task 012, 2026-10-04).
Everything below was run in the development container (Linux, Python 3.14.8,
Node.js 22, PostgreSQL 18.4, Chromium 1194). Nothing here is extrapolated: an
item that could not be run is listed as **not run** or **pending**.

## Summary

| Area | Result |
| --- | --- |
| Backend tests (pytest) | 543 passed, 0 failed, 1 skipped (real OpenCLIP weights unavailable), 90 s |
| Lint | ruff clean (0.15 and 0.16 with `backend/ruff.toml`); `npm run lint` clean |
| Frontend build | `npm ci` + `npm run build` succeed |
| Clean install from zero | passed (fresh clone, fresh virtualenv, empty database) |
| Migration round trip | upgrade → downgrade base → upgrade, `alembic check` clean both times |
| Browser checks (Chromium) | 295/295 checks on demo data; demo-path E2E 17/17; earlier feature suites 316/316 |
| Accessibility (axe-core) | 0 violations of any impact on the major routes |
| Dependency audit | pip-audit: no known vulnerabilities; npm runtime: 0; npm dev-only: 5 high (one `braces` advisory, not applicable at runtime) |
| Secret scan | clean (placeholders only) |
| Data integrity | all invariants hold on the demo data (`python -m app.db.check_integrity`) |
| Visual search | architecture, UI and test-encoder verified; **real OpenCLIP validation pending** |
| Smart Fit | technically functional with the real model; **accuracy not validated** |

No critical or high-severity application bug is open.

## 1. Backend

- `pytest` (from `backend/`, main virtualenv): **543 passed, 1 skipped, 0
  failed**, 90 s (earlier runs 90–120 s). The skipped test needs the real OpenCLIP weights.
- Clean environment (requirements-dev only, no AI extras): 540 passed, 2
  skipped (OpenCLIP and MediaPipe optional tests), 88–110 s.
- New tests in this task:
  - `test_authorization_matrix.py` (70 tests): every admin operation from the
    OpenAPI schema (34) answers 403 to a customer and 401 to a visitor;
    customer A gets 404 on 12 operations on customer B's orders, returns,
    conversations, addresses and cart items.
  - `test_demo_reset.py` (4 tests): the demo dataset satisfies every
    integrity check (inside a rolled-back transaction); the reset refuses
    to run without `--yes`, with placeholder passwords, in production or
    against a remote host.
  - `test_config.py`: weak/placeholder JWT secrets are refused.
- `ruff check app tests` and `ruff format --check app tests`: clean.

## 2. Clean install and database from zero

A fresh clone with the release changes applied, a new Python 3.14 virtualenv
(`pip install -r requirements-dev.txt`) and an empty database:

1. `alembic upgrade head` (7 migrations), `alembic check`: no drift.
2. `alembic downgrade base`, `alembic upgrade head`, `alembic check`: no drift.
3. `python -m app.db.reset_demo --yes` → presentation data;
   `python -m app.db.check_integrity` → "All invariants hold."
4. `pytest`, `ruff`: as above.
5. `frontend`: `npm ci` (372 packages), `npm run lint`, `npm run build`: OK.
6. `python -m app.demo.healthcheck`: all checks OK except the two optional AI
   models, which were not prepared in that run (expected).

Finding fixed: ruff 0.16 enables more rules by default and failed on the
fresh install; `backend/ruff.toml` now fixes the rule set and
`requirements-dev.txt` pins `ruff>=0.15,<0.17`.

## 3. Dependency audit

| Tool | Scope | Result | Classification |
| --- | --- | --- | --- |
| pip-audit | `requirements.txt`, `requirements-smart-fit.txt`, `requirements-visual-search.txt`, installed environment | No known vulnerabilities | — |
| npm audit --omit=dev | runtime packages | 0 vulnerabilities | — |
| npm audit | all packages | 5 high | Dev only: one advisory (`braces`, GHSA-vfj7-8cjw-p6xm) reached through `eslint-config-next`. Not shipped to the browser or server. The suggested `--force` fix downgrades eslint-config-next to 14.x and was **not** applied. |

Test tools (pytest, httpx2, ruff) moved from `requirements.txt` to
`requirements-dev.txt`, so a demo install doesn't carry them.

## 4. Security review

Full write-up: [security-privacy.md](security-privacy.md). Results:

- **Secrets**: no `.env`, keys, tokens or real passwords tracked; only
  `CHANGE_ME` placeholders in `.env.example`. Startup refuses placeholder or
  weak JWT secrets; the demo reset refuses placeholder passwords.
- **Authentication**: Argon2id, short-lived JWT, rotating single-use refresh
  tokens with reuse detection, revocation on logout/password change, rate
  limits on login/registration. No public admin registration; admins only via
  `create_admin` or the demo reset.
- **Authorization**: matrix tested (section 1); ownership is enforced in the
  API, never in the frontend.
- **CSRF**: Server Actions check Origin (Next.js). **Fixed in this task**: the
  three cookie-authenticated POST route handlers (support messages for
  customer and admin, Smart Fit estimate) now reject a missing or foreign
  `Origin` with 403. Verified with curl.
- **Commerce trust**: prices, totals, delivery fees, stock, payment/refund
  states and roles are never taken from the browser (tests cover tampered
  inputs).
- **XSS**: no `dangerouslySetInnerHTML`, `innerHTML` or `eval`; user text is
  rendered by React; redirect targets go through `safeNextPath`.
- **Files and images**: content-type sniffing, size and dimension limits,
  in-memory decoding, EXIF removed, nothing stored.
- **Privacy**: data inventory documented; search and body photos are never
  stored; no card data.

## 5. Data integrity

`python -m app.db.check_integrity` (read-only) verifies: stock never negative,
on hand ≥ reserved, reserved = units in open orders, order and line totals,
order and return histories ending in the current status, returned ≤ purchased,
returns only for delivered orders, restock only for received/refunded returns,
refund amount only and exactly for refunded returns, and conversation
timestamps. **All hold** on the demo data and after the browser E2E runs.

## 6. Browser checks (Chromium only)

Firefox and Safari/WebKit were **not tested** (not available in the
environment).

**Final pass on the demo data**: 295/295 checks.

- Customer routes at 1440, 1366, 1280, 1024, 768 and 390 px; admin routes at
  1440, 1280, 1024, 768 and 390 px: no horizontal overflow, no off-screen
  controls, no page errors.
- 102 internal links resolve (crawled as visitor, customer and admin); no
  `href="#"` placeholders.
- **axe-core** (WCAG 2 A/AA, 2.1 AA, best practices) at 1440/390 (customer)
  and 1440/768 (admin): **0 critical, 0 serious, 0 moderate, 0 minor**.

Fixed in this task: admin visual-search lists were scrollable but not
keyboard-focusable (serious); shop heading order at 390 px (moderate); the
admin dashboard squeezed the recent-orders table at 1440 px (panels now
stack below 1536 px); product pages linked to a missing delivery page (new
`/help/delivery`); a footer FAQ link pointed nowhere (removed).

**Demo-path E2E** (`docs/demo/README.md` customer + admin paths): 17/17,
including Smart Fit with test photos, checkout, return request and support
replies appearing for the customer.

**Feature regression suites** (run on the plain seed data): storefront 44/44,
auth 41/41, commerce 48/48, admin 59/59, Smart Fit 41/41, returns 27/27,
support chat 27/27, visual search unavailable state 9/9, visual search with a
test encoder 20/20.

Accessibility limits: automated checks and keyboard tests only; no
screen-reader user testing.

## 7. Performance

Production build, local machine, medians of repeated requests:

| Request | Median |
| --- | --- |
| Home page (SSR) | 71 ms |
| Shop page | 45 ms |
| Product page | 48 ms |
| API catalog list / product detail | 20 / 9 ms |
| Checkout quote / order creation | 46 / 44 ms |
| Admin overview | 23 ms |
| Support conversation / poll | 18 / 9 ms |
| Smart Fit inference per photo | ≈ 100–220 ms (model load 0.7–19 s when cold) |

**N+1 check**: every list and detail endpoint issues a constant 3–9 SQL
queries regardless of row count (catalog 5, orders 4, order detail 4, return
detail 6, conversation 8, admin overview 9, admin order detail 7).

## 8. AI validation status

### Visual search

- Architecture verified
- UI verified
- Test encoder verified
- **Real OpenCLIP validation pending because the model host is
  inaccessible.** The ViT-B-32 / laion2b_s34b_b79k weights could not be
  downloaded (huggingface.co and download.pytorch.org are blocked by the
  development environment's network policy; re-attempted 2026-10-04). Result
  quality and thresholds with the real model are unverified. To validate:
  `python -m app.ai.prepare_visual_search`, `python -m app.ai.visual_search_index`,
  `python -m app.ai.evaluate_visual_search` on a machine with internet access.

### Smart Fit

Smart Fit is technically functional, but real-world measurement accuracy has
not yet been validated against ground-truth tape measurements. The real
MediaPipe Pose Landmarker model was downloaded, SHA-256 verified and run
(`prepare_smart_fit` self-test "Ready"; E2E with test images). No volunteer
measurements were taken, and none are claimed.

### Claims review

UI and docs were reviewed for unsupported claims. Changed: "Recommended for
you" (not personalised) → "Popular picks"; the hero Smart Fit card is labelled
as an example; "precise delivery" wording removed. Accuracy figures, "AI
picks for you" style wording and production-readiness claims are absent.

## 9. Demo readiness

See [demo/README.md](demo/README.md).

- `python -m app.db.reset_demo --yes`: deterministic presentation data;
  refuses unsafe environments; credentials from `DEMO_*` variables only.
- `python -m app.demo.healthcheck`: on the demo setup every check passes
  except "Visual search index: 0/69" (weights unavailable, see section 8).
- Offline readiness: `prepare_smart_fit --offline` → Ready;
  `prepare_visual_search --offline` cannot pass until the weights are
  prepared.
- Startup, recovery plan, live and backup Smart Fit paths, and a local
  visual-search photo are documented. The release contains no photos of real
  people.
- Screenshots: `docs/screenshots/` (18 images, 1440 × 900 full page, taken
  after a demo reset).

## 10. Known limitations

See the README's "Known limitations": simulated payments and refunds, no
courier integration, pending visual-search validation, unvalidated Smart Fit
accuracy, generic size charts, polling support chat, process-local rate
limits, no uploads, favorites per visit, Chromium-only browser testing.
