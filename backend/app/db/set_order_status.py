"""Change an order's status from the command line (demo/setup tooling).

There is no admin dashboard yet. This lets a developer move an order along
the tracking timeline:

    python -m app.db.set_order_status KW-2026-7K4M9Q shipped --note "Left Douala hub"

Statuses: confirmed, preparing, shipped, out_for_delivery, delivered, cancelled.
Only valid next steps are accepted (see ORDER_TRANSITIONS in services/orders.py);
delivered and cancelled also update inventory. The admin dashboard
(/admin/orders) does the same thing in the browser.
"""

import argparse
import sys

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models import Order, OrderStatus
from app.services.errors import ServiceError
from app.services.orders import change_status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("order_number")
    parser.add_argument(
        "status", choices=[s.value for s in OrderStatus if s != OrderStatus.pending]
    )
    parser.add_argument("--note", default=None)
    args = parser.parse_args(argv)

    with SessionLocal() as db:
        order = db.scalar(
            select(Order)
            .where(Order.order_number == args.order_number.strip().upper())
            .options(selectinload(Order.items), selectinload(Order.status_history))
        )
        if order is None:
            print(f"No order {args.order_number}.", file=sys.stderr)
            return 1
        try:
            change_status(db, order, OrderStatus(args.status), args.note)
        except ServiceError as exc:
            print(exc.message, file=sys.stderr)
            return 1
        db.commit()
        print(f"{order.order_number} is now {order.status.value}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
