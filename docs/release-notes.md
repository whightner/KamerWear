# KamerWear v1.0.0-demo — release notes

**Academic/demo MVP.** A fashion e-commerce prototype for Cameroon built as a
two-week school project. It is not production-certified: payments, couriers
and notifications are simulated or absent, and the two AI features are
prototypes with documented validation gaps.

## What's included

**Customers**: registration and login, profile and password change, Cameroon
delivery addresses, catalog with search, filters and sorting, product pages
with colour/size variants and live stock, favorites (current visit), cart
(saved to the account, guest cart merged at login), server-calculated
checkout with demo payment methods, order history with a tracking timeline,
visual search by photo, Smart Fit size recommendations, returns, and support
conversations.

**Store staff** (`/admin`): dashboard, products, categories, variants, image
metadata, inventory, order fulfilment with a strict state machine, manual
(demo) payment states, returns processing with per-item restock decisions and
demo refunds, support replies, and the visual-search index.

**AI features**
- Visual search: pretrained OpenCLIP ViT-B-32 embeddings + cosine similarity +
  a zero-shot type guard. *Real weights not yet validated* (model host blocked
  in the development environment).
- Smart Fit: pretrained MediaPipe Pose Landmarker + height-scaled outline
  geometry + versioned demo size charts; customers always review and confirm.
  *Real-world measurement accuracy not yet validated* against tape
  measurements.

## Changes in the final QA task (Task 012)

- `python -m app.db.reset_demo --yes`: clean, deterministic presentation data
  (believable stock, six orders in useful states, an active and a refunded
  return, two support conversations, fictional customers; accounts from
  `DEMO_*` environment variables). Refuses unsafe environments.
- `python -m app.db.check_integrity`: read-only inventory/order/return/support
  invariants.
- `python -m app.demo.healthcheck`: pre-demo checklist (database, API, web,
  logins, visual index, Smart Fit model).
- Security: Origin check on cookie-authenticated POST route handlers (CSRF
  defence in depth); demo reset refuses placeholder passwords.
- Accessibility: scrollable admin list made keyboard-focusable; shop results
  heading order fixed.
- Content: homepage "Recommended for you" (not personalised) renamed
  "Popular picks"; hero Smart Fit card labelled as an example; "precise
  delivery" wording removed.
- Links: new `/help/delivery` page (was a 404 from product pages); footer FAQ
  link (no FAQ exists) removed.
- Dependencies: test tools moved to `requirements-dev.txt`.
- Tests: authorization matrix (all admin routes as customer/visitor,
  cross-customer access), demo-reset consistency, JWT-secret validation.
- Documentation: final README, architecture overview, ER description, API
  inventory, security & privacy review, demo guide, QA report.

## Upgrade / install

Fresh install: see the README ("Setup from zero"). Existing development
databases: `alembic upgrade head` (no schema change in Task 012).

## Known limitations

See the README's "Known limitations" section; they apply unchanged to this
release.
