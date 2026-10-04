"""Check data invariants in the configured database (read-only).

    python -m app.db.check_integrity

Exits with 1 if any invariant is broken. Checks:
- inventory: on_hand >= 0, reserved >= 0, on_hand >= reserved, and reserved
  equals the units of open orders (pending to out_for_delivery);
- orders: totals add up, the last history entry matches the status;
- returns: per order line, units in active returns <= units purchased; the
  history ends with the current status; restock decisions exist exactly for
  received/refunded returns; a refund amount exists exactly for refunded ones;
- support: last_message_at matches the newest message.
"""

import sys

from sqlalchemy import text

from app.db.session import SessionLocal

OPEN = "('pending','confirmed','preparing','shipped','out_for_delivery')"
ACTIVE_RETURNS = "('requested','approved','received','refunded')"

CHECKS: list[tuple[str, str]] = [
    (
        "inventory never negative",
        "SELECT variant_id FROM inventory WHERE on_hand < 0 OR reserved < 0",
    ),
    ("inventory on_hand >= reserved", "SELECT variant_id FROM inventory WHERE on_hand < reserved"),
    (
        "reserved = units of open orders",
        f"""SELECT i.variant_id, i.reserved, COALESCE(o.units, 0)
            FROM inventory i
            LEFT JOIN (SELECT oi.variant_id, SUM(oi.quantity) AS units
                       FROM order_items oi JOIN orders o ON o.id = oi.order_id
                       WHERE o.status IN {OPEN} GROUP BY oi.variant_id) o
              ON o.variant_id = i.variant_id
            WHERE i.reserved <> COALESCE(o.units, 0)""",
    ),
    (
        "order totals add up",
        """SELECT o.order_number FROM orders o
           WHERE o.subtotal <> (SELECT COALESCE(SUM(line_total), 0) FROM order_items
                                WHERE order_id = o.id)
              OR o.total <> o.subtotal + o.delivery_fee - o.discount_total""",
    ),
    (
        "order lines: line_total = unit_price x quantity",
        "SELECT id FROM order_items WHERE line_total <> unit_price * quantity",
    ),
    (
        "order history ends with the order status",
        """SELECT o.order_number FROM orders o
           WHERE o.status <> (SELECT h.status FROM order_status_history h
                              WHERE h.order_id = o.id ORDER BY h.id DESC LIMIT 1)""",
    ),
    (
        "returned units <= purchased units",
        f"""SELECT oi.id, oi.quantity, SUM(ri.quantity)
            FROM return_items ri
            JOIN return_requests r ON r.id = ri.return_request_id
            JOIN order_items oi ON oi.id = ri.order_item_id
            WHERE r.status IN {ACTIVE_RETURNS}
            GROUP BY oi.id, oi.quantity HAVING SUM(ri.quantity) > oi.quantity""",
    ),
    (
        "returns only for delivered orders",
        """SELECT r.return_number FROM return_requests r JOIN orders o ON o.id = r.order_id
           WHERE o.status <> 'delivered'""",
    ),
    (
        "return history ends with the return status",
        """SELECT r.return_number FROM return_requests r
           WHERE r.status <> (SELECT h.status FROM return_status_history h
                              WHERE h.return_request_id = r.id ORDER BY h.id DESC LIMIT 1)""",
    ),
    (
        "restock decided exactly for received/refunded returns",
        """SELECT r.return_number FROM return_requests r JOIN return_items ri
             ON ri.return_request_id = r.id
           WHERE (r.status IN ('received','refunded')) <> (ri.restock IS NOT NULL)""",
    ),
    (
        "refund amount exactly for refunded returns",
        """SELECT return_number FROM return_requests
           WHERE (status = 'refunded') <> (refunded_amount IS NOT NULL)""",
    ),
    (
        "each status reached at most once per return",
        """SELECT return_request_id, status FROM return_status_history
           GROUP BY return_request_id, status HAVING COUNT(*) > 1""",
    ),
    (
        "conversation last_message_at = newest message",
        """SELECT c.conversation_number FROM support_conversations c
           WHERE c.last_message_at < (SELECT MAX(m.created_at) FROM support_messages m
                                      WHERE m.conversation_id = c.id)""",
    ),
]


def main() -> int:
    failed = 0
    with SessionLocal() as db:
        for name, sql in CHECKS:
            rows = db.execute(text(sql)).all()
            status = "ok" if not rows else f"FAILED ({len(rows)}): {rows[:5]}"
            failed += bool(rows)
            print(f"{'✓' if not rows else '✗'} {name}: {status}")
    print("All invariants hold." if not failed else f"{failed} invariant(s) broken.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
