"""The demo reset builds a consistent presentation state (in a rolled-back transaction)."""

import pytest
from sqlalchemy import func, select, text

from app.db import reset_demo
from app.db.check_integrity import CHECKS
from app.db.create_admin import create_admin
from app.models import (
    Inventory,
    Order,
    OrderStatus,
    ReturnRequest,
    ReturnStatus,
    SupportConversation,
)


def test_demo_dataset_is_consistent(db_session):
    reset_demo.wipe(db_session)
    stock = reset_demo.presentation_stock(db_session)
    assert stock["low"] == 5 and stock["sold_out"] == 3 and stock["normal"] > 150
    admin = create_admin(
        db_session, "manager@example.com", "a demo pass phrase", "Store", "Manager"
    )
    amina, usable = reset_demo.make_customer(
        db_session, "amina@example.com", "another pass phrase", "Amina", "Ndongo", "+237677102030"
    )
    brice, _ = reset_demo.make_customer(db_session, "b@example.com", None, "Brice", "M", "+237699")
    clarisse, _ = reset_demo.make_customer(db_session, "c@example.com", None, "Cla", "F", "+237655")
    assert usable is True
    summary = reset_demo.demo_data(db_session, admin, amina, brice, clarisse)
    db_session.flush()

    statuses = sorted(s.value for s in db_session.scalars(select(Order.status)))
    assert statuses == sorted(
        ["confirmed", "shipped", "delivered", "delivered", "delivered", "pending"]
    )
    returns = {r.status for r in db_session.scalars(select(ReturnRequest))}
    assert returns == {ReturnStatus.requested, ReturnStatus.refunded}
    assert db_session.scalar(select(func.count(SupportConversation.id))) == 2
    assert len(summary) == 7
    for name, sql in CHECKS:
        assert db_session.execute(text(sql)).all() == [], name
    low = db_session.scalar(
        select(func.count(Inventory.id)).where(
            Inventory.on_hand - Inventory.reserved > 0, Inventory.on_hand - Inventory.reserved <= 5
        )
    )
    assert low <= 10  # a believable store, not hundreds of alerts
    assert (
        db_session.scalar(select(func.count(Order.id)).where(Order.status == OrderStatus.delivered))
        == 3
    )


@pytest.mark.parametrize(
    ("argv", "env", "message"),
    [
        ([], {}, "--yes"),
        (["--yes"], {"APP_ENV": "production"}, "production"),
    ],
)
def test_reset_refuses_unsafe_runs(monkeypatch, capsys, argv, env, message):
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(SystemExit) as exit_info:
        reset_demo.main(argv)
    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err


def test_reset_refuses_remote_database(monkeypatch, capsys):
    monkeypatch.setattr(
        reset_demo.settings, "database_url", "postgresql+psycopg://u@db.example.com/kamerwear"
    )
    with pytest.raises(SystemExit):
        reset_demo.main(["--yes"])
    assert "not local" in capsys.readouterr().err
