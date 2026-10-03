# Authentication and sessions

Customer accounts (Task 006): registration, login, logout, profile and password
change. No social login, password-reset email or email verification yet.

## Flow

```
Browser ──(HttpOnly cookies kw_access / kw_refresh)──> Next.js server
                                                         │  Server Actions, proxy.ts,
                                                         │  Server Components
                                                         ▼
                                   FastAPI  (Authorization: Bearer <access token>)
                                                         │
                                                         ▼
                                   PostgreSQL (users, user_profiles, auth_sessions)
```

- **FastAPI is cookie-free.** It returns tokens in JSON and reads only the
  `Authorization: Bearer` header, so a future mobile app can use the same
  endpoints and keep its tokens in secure device storage.
- **The web app keeps the tokens on the server side of the browser.** Next.js
  Server Actions call FastAPI and store the tokens in `HttpOnly` cookies on the
  Next.js origin. Browser JavaScript never sees a token: nothing goes into
  `localStorage`, `sessionStorage`, React state or the HTML. Pages only receive
  the user fields they display (e.g. the first name in the header).

## Tokens

| Token | Lifetime | Contents |
| --- | --- | --- |
| Access | 15 min (`ACCESS_TOKEN_EXPIRE_MINUTES`) | `sub` (user id), `sid` (session id), `type=access`, `iat`, `exp` |
| Refresh | 7 days (`REFRESH_TOKEN_EXPIRE_DAYS`) | as above with `type=refresh` and a `jti` |

- Signed with HS256 using `JWT_SECRET_KEY` (PyJWT). The algorithm is fixed when
  decoding, and `exp`, `iat`, `sub`, `sid` and `type` are required. The API
  refuses to start auth without a secret of at least 32 characters; the
  `CHANGE_ME…` placeholder is rejected.
- Every login creates an `auth_sessions` row. Each authenticated request
  checks that the session is still active, so **logout and password changes
  take effect immediately**, not when the access token expires.
- **Refresh tokens are single-use (rotation).** `POST /auth/refresh` returns a
  new pair and records the new `jti`. Presenting an older refresh token revokes
  the whole session (likely a stolen copy).
- Changing the password revokes all of the user's other sessions; the current
  one stays signed in.

## Cookies (web)

`kw_access` and `kw_refresh`: `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` when
`NODE_ENV=production` (override with `AUTH_COOKIE_SECURE=true|false`, e.g. to
test a production build over plain `http://localhost`). Max-Age matches the
token lifetime.

## Keeping the session fresh

`frontend/src/proxy.ts` runs before each page request and Server Action:

1. If the access token is missing or expires within 30 s and a refresh token
   exists, it calls `/auth/refresh` and updates both the request (so this render
   uses the new token) and the response cookies.
2. If the refresh fails with 401, the cookies are deleted; on `/account*` the
   visitor is redirected to `/login?next=…&reason=expired`.
3. If the API is unreachable, nothing is deleted (a restart doesn't log users out).
4. Concurrent requests (e.g. link prefetches) share one refresh call, so
   rotation doesn't mistake them for token reuse. That de-duplication is
   in-memory, which suits the single Next.js server of the MVP.

## Protected routes

- `/account` and `/account/profile` call `requireUser()` in the Server
  Component, which asks FastAPI for `/users/me` and redirects to
  `/login?next=<path>` when there is no valid session. Nothing private is
  rendered before that check, so there is no flash of account content.
- `proxy.ts` does a quick cookie-only check first (no cookies → redirect),
  but it is an optimisation; the page check is the real one.
- `next` only accepts same-site paths (`/…`, never `//…` or `\`), so the login
  page can't be used as an open redirect.

## CSRF

- State-changing web requests are Server Actions: POST only, and Next.js
  rejects them when the `Origin` header doesn't match the host.
- The cookies are `SameSite=Lax`: browsers don't attach them to cross-site
  POSTs, fetches or iframes.
- FastAPI ignores cookies entirely (Bearer header only), so a cross-site form
  posted straight at the API carries no credentials.
- Logout is a POST form, never a GET link.

## CORS

FastAPI allows only the origins in `CORS_ORIGINS`; `*` is rejected at startup
because credentials are allowed. The browser doesn't call FastAPI for auth at
all (the Next.js server does).

## Passwords

- Argon2id via `argon2-cffi` (RFC 9106 low-memory profile). Hashes are
  upgraded on login if the parameters change. Plaintext is never stored or
  logged.
- Policy: 10–128 characters, not only spaces, not equal to the email. Long
  passphrases are accepted as typed and never truncated or trimmed.
- Login answers "Email or password is incorrect." for both a wrong password and
  an unknown email, and runs a dummy hash for unknown emails so timing is
  similar.

## Rate limiting (not production-grade)

In-memory sliding windows in `backend/app/core/rate_limit.py`:

| Action | Limit |
| --- | --- |
| Failed logins per email | 5 per 15 min |
| Failed logins per IP | 30 per 15 min |
| Registrations per IP | 10 per hour |

Exceeding a limit returns `429 too_many_attempts` with `Retry-After`. The
counters live in one process and reset on restart. A real deployment should
rate-limit at the reverse proxy or in a shared store. `X-Forwarded-For` is
only trusted from `TRUSTED_PROXY_IPS` (the local Next.js server by default).

## Roles and admins

Public registration always creates a `customer`; `role`, `is_active` and
`is_verified` are rejected if sent. Admins are created only from the command
line, with credentials typed at the prompt or passed via environment
variables (never stored in the repository):

```bash
cd backend
python -m app.db.create_admin                 # prompts for email, name, password
# or non-interactively:
ADMIN_EMAIL=... ADMIN_FIRST_NAME=... ADMIN_LAST_NAME=... ADMIN_PASSWORD=... python -m app.db.create_admin
```

There is no admin dashboard yet.
