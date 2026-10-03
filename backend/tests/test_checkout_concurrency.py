"""Real concurrent checkouts on PostgreSQL (separate connections, committed data).

These don't use the rolled-back test transaction, so they create their own
customers and clean up afterwards.
"""

import threading
import uuid

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Address, Cart, CartItem, Inventory, Order, PaymentMethod, User
from app.schemas.orders import OrderCreate
from app.services import orders
from app.services.errors import ServiceError

SKU = "CBJ-GREEN-L"


@pytest.fixture
def last_unit(db_engine):
    """Two customers, each with the last unit of SKU in their cart."""
    with Session(db_engine) as db:
        inventory = db.scalar(
            select(Inventory).join(Inventory.variant).where(Inventory.variant.has(sku=SKU))
        )
        original = (inventory.on_hand, inventory.reserved)
        inventory.on_hand, inventory.reserved = 1, 0
        users = []
        for name in ("race-a", "race-b"):
            user = User(email=f"{name}-{uuid.uuid4().hex[:8]}@kamerwear.cm", password_hash="x")
            db.add(user)
            db.flush()
            address = Address(
                user_id=user.id,
                label="Home",
                recipient_name=name,
                phone="+237699000000",
                region="Littoral",
                city="Douala",
                quarter="Akwa",
                street_or_landmark="Near a",
                is_default=True,
            )
            db.add_all(
                [
                    address,
                    Cart(
                        user_id=user.id,
                        items=[CartItem(variant_id=inventory.variant_id, quantity=1)],
                    ),
                ]
            )
            db.flush()
            users.append((user.id, address.id))
        db.commit()
    yield users
    with Session(db_engine) as db:
        ids = [user_id for user_id, _ in users]
        db.execute(delete(User).where(User.id.in_(ids)))
        inventory = db.scalar(
            select(Inventory).join(Inventory.variant).where(Inventory.variant.has(sku=SKU))
        )
        inventory.on_hand, inventory.reserved = original
        db.commit()


def _checkout(db_engine, user_id, address_id, key, barrier, results):
    with Session(db_engine) as db:
        user = db.get(User, user_id)
        data = OrderCreate(address_id=address_id, payment_method=PaymentMethod.cash_on_delivery)
        barrier.wait()
        try:
            order, created = orders.create_order(db, user, data, key)
            db.commit()
            results.append(("ok", order.order_number, created))
        except ServiceError as exc:
            db.rollback()
            results.append(("error", exc.code, None))


def _run(db_engine, jobs):
    barrier = threading.Barrier(len(jobs))
    results: list = []
    threads = [
        threading.Thread(target=_checkout, args=(db_engine, *job, barrier, results)) for job in jobs
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    return results


def test_last_unit_cannot_be_sold_twice(db_engine, last_unit):
    (a, a_address), (b, b_address) = last_unit
    results = _run(db_engine, [(a, a_address, uuid.uuid4().hex), (b, b_address, uuid.uuid4().hex)])
    outcomes = sorted(r[0] for r in results)
    assert outcomes == ["error", "ok"], results
    assert next(r for r in results if r[0] == "error")[1] == "insufficient_stock"
    with Session(db_engine) as db:
        inventory = db.scalar(
            select(Inventory).join(Inventory.variant).where(Inventory.variant.has(sku=SKU))
        )
        assert (inventory.on_hand, inventory.reserved) == (1, 1)
        assert db.query(Order).filter(Order.user_id.in_([a, b])).count() == 1


def test_simultaneous_double_submit_creates_one_order(db_engine, last_unit):
    (a, a_address), _ = last_unit
    key = uuid.uuid4().hex
    results = _run(db_engine, [(a, a_address, key), (a, a_address, key)])
    assert [r[0] for r in results] == ["ok", "ok"], results
    assert results[0][1] == results[1][1]
    assert sorted(r[2] for r in results) == [False, True]
    with Session(db_engine) as db:
        assert db.query(Order).filter(Order.user_id == a).count() == 1
