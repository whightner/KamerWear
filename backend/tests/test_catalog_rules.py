"""Pure catalog rules that need no database."""

import pytest

from app.db.seed import distribute, sku_for, sku_prefix
from app.models import Inventory
from app.models.catalog import discount_percent


@pytest.mark.parametrize(
    ("price", "compare_at", "expected"),
    [
        (28500, 39900, 29),
        (5500, 8000, 31),
        (14500, 19500, 26),
        (11000, None, None),
        (100, 100, None),
    ],
)
def test_discount_percent_rounds_like_the_frontend(price, compare_at, expected):
    assert discount_percent(price, compare_at) == expected


def test_available_inventory_is_never_negative():
    assert Inventory(on_hand=5, reserved=2).available == 3
    assert Inventory(on_hand=1, reserved=4).available == 0


def test_sku_format():
    assert sku_prefix("urban-runner-02") == "UR02"
    assert sku_for("classic-hoodie", "olive", "M") == "CH-OLIVE-M"
    assert sku_for("weekend-duffel", "navy", None) == "WD-NAVY-OS"


def test_distribute_keeps_the_total():
    assert distribute(5, 5) == [1, 1, 1, 1, 1]
    assert distribute(4, 9) == [1, 1, 1, 1, 0, 0, 0, 0, 0]
    assert sum(distribute(22, 12)) == 22
    assert distribute(3, 0) == []
