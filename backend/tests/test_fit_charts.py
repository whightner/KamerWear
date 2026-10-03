"""Size suggestions from the demo charts (no model involved)."""

import pytest

from app.fit import charts


def test_charts_are_versioned_and_complete():
    assert charts.chart_version().startswith("kamerwear-demo-")
    assert charts.top_sizes() == ["XS", "S", "M", "L", "XL", "XXL"]
    assert charts.bottom_sizes() == ["28", "30", "32", "34", "36", "38", "40"]
    assert charts.bottom_letter("32") == "M"
    assert charts.shoe_range() == (35, 48)


@pytest.mark.parametrize(
    ("chest", "size"), [(85, "XS"), (88, "S"), (99.9, "M"), (100, "M"), (111.9, "L"), (127, "XXL")]
)
def test_top_size_by_chest(chest, size):
    assert charts.suggest_top(chest, "regular").size == size


@pytest.mark.parametrize(
    ("chest", "preference", "size"),
    [
        (97, "slim", "S"),  # lowest quarter of M -> one size down
        (97, "regular", "M"),
        (97, "relaxed", "M"),
        (103, "relaxed", "L"),  # near the M/L boundary -> one size up
        (103, "regular", "M"),
        (103, "slim", "M"),
        (100, "slim", "M"),  # middle of the range: no shift
        (100, "relaxed", "M"),
        (81, "slim", "XS"),  # already the smallest size
        (127, "relaxed", "XXL"),  # already the largest
    ],
)
def test_fit_preference_only_shifts_at_boundaries(chest, preference, size):
    assert charts.suggest_top(chest, preference).size == size


def test_outside_the_chart_uses_the_nearest_size_with_a_note():
    small, large = charts.suggest_top(70, "regular"), charts.suggest_top(140, "regular")
    assert (small.size, large.size) == ("XS", "XXL")
    assert "smallest" in small.note and "largest" in large.note


def test_missing_measurement_gives_no_suggestion():
    assert charts.suggest_top(None, "regular") is None
    assert charts.suggest_bottom(None, None, "regular") is None


def test_trousers_take_the_larger_of_waist_and_hip_sizes():
    assert charts.suggest_bottom(82, None, "regular").size == "32"
    assert charts.suggest_bottom(None, 103, "regular").size == "34"
    assert charts.suggest_bottom(82, 103, "regular").size == "34"
    assert charts.suggest_bottom(95, 97, "regular").size == "36"
