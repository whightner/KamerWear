"""Pre-presentation health check. Read-only; prints one line per check.

    python -m app.demo.healthcheck [--api http://127.0.0.1:8000] [--web http://127.0.0.1:3000]

Logins use DEMO_ADMIN_EMAIL / DEMO_ADMIN_PASSWORD and DEMO_CUSTOMER_EMAIL /
DEMO_CUSTOMER_PASSWORD from the environment (skipped when not set). Exits
with the number of failed checks.
"""

import argparse
import json
import os
import urllib.error
import urllib.request

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal


def _request(url: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw, status = exc.read(), exc.code
    try:
        return status, json.loads(raw or b"{}")
    except json.JSONDecodeError:
        return status, {}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that the demo is ready.")
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    parser.add_argument("--web", default="http://127.0.0.1:3000")
    args = parser.parse_args(argv)
    api = args.api.rstrip("/") + "/api/v1"
    results: list[tuple[str, bool, str]] = []

    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as exc:  # report, never crash the checklist
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        results.append((name, ok, detail))
        return ok

    def database():
        with SessionLocal() as db:
            version = db.execute(text("SHOW server_version")).scalar()
            products = db.execute(text("SELECT COUNT(*) FROM products WHERE is_active")).scalar()
        return products > 0, f"PostgreSQL {version}, {products} active products"

    def api_health():
        status, body = _request(f"{api}/health")
        return status == 200, f"{status} {body.get('status', '')}".strip()

    def web():
        with urllib.request.urlopen(args.web, timeout=15) as response:
            return response.status == 200, f"{response.status}"

    tokens = {}

    def login(kind):
        email = os.environ.get(f"DEMO_{kind.upper()}_EMAIL")
        password = os.environ.get(f"DEMO_{kind.upper()}_PASSWORD")
        if not (email and password):
            return False, f"DEMO_{kind.upper()}_EMAIL/PASSWORD not set"
        status, body = _request(f"{api}/auth/login", {"email": email, "password": password})
        if status != 200:
            return False, f"login failed ({status})"
        tokens[kind] = body["access_token"]
        role = body["user"]["role"]
        expected = "admin" if kind == "admin" else "customer"
        return role == expected, f"{email} ({role})"

    def visual_index():
        if "admin" not in tokens:
            return False, "needs the admin login"
        status, body = _request(f"{api}/admin/visual-search/status", token=tokens["admin"])
        if status != 200:
            return False, f"status {status}"
        detail = (
            f"{body['indexed_images']}/{body['active_images']} photos indexed, "
            f"model {body['model']} ({body['encoder_state']})"
        )
        return body["ready"] and not body["unindexed_images"] and not body["stale_images"], detail

    def smart_fit():
        from app.fit.pose import MODEL_SHA256, file_sha256, model_path

        path = model_path()
        if not path.is_file():
            return False, "model file missing: python -m app.ai.prepare_smart_fit"
        if file_sha256(path) != MODEL_SHA256:
            return False, "model file doesn't match the pinned SHA-256"
        import mediapipe  # noqa: F401  (raises if the package is missing)

        return True, f"{path.name} present, mediapipe importable"

    check("Database", database)
    check("API /health", api_health)
    check("Next.js reachable", web)
    check("Admin login", lambda: login("admin"))
    check("Customer login", lambda: login("customer"))
    check("Visual search index", visual_index)
    check("Smart Fit model", smart_fit)

    print(f"KamerWear demo health check ({settings.database_url.split('@')[-1]})")
    for name, ok, detail in results:
        print(f"  {'✓' if ok else '✗'} {name}: {detail}")
    failed = sum(not ok for _, ok, _ in results)
    print("Ready for the demo." if not failed else f"{failed} check(s) need attention.")
    return failed


if __name__ == "__main__":
    raise SystemExit(main())
