"""Demo size charts and the size-suggestion rules (no AI here).

The charts live in size_charts.json so they are easy to read and change. A
suggestion picks the size whose range contains the estimated measurement,
then the fit preference may move one size at a range boundary.
"""

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

CHARTS_FILE = Path(__file__).with_name("size_charts.json")


@cache
def charts() -> dict:
    return json.loads(CHARTS_FILE.read_text(encoding="utf-8"))


def chart_version() -> str:
    return charts()["version"]


def top_sizes() -> list[str]:
    return [row["size"] for row in charts()["tops"]["sizes"]]


def bottom_sizes() -> list[str]:
    return [row["size"] for row in charts()["bottoms"]["sizes"]]


def bottom_letter(size: str) -> str | None:
    """Letter equivalent of a numeric trouser size (for S/M/L trousers)."""
    for row in charts()["bottoms"]["sizes"]:
        if row["size"] == size:
            return row["letter"]
    return None


def shoe_range() -> tuple[int, int]:
    shoes = charts()["shoes"]
    return shoes["eu_min"], shoes["eu_max"]


@dataclass(frozen=True)
class Suggestion:
    size: str
    note: str | None = None  # e.g. "between M and L" or "above the largest size"


def _pick(rows: list[dict], key: str, value: float, preference: str) -> Suggestion:
    """Size for one measurement, with the fit-preference shift at boundaries."""
    sizes = [row["size"] for row in rows]
    first_min, last_max = rows[0][key][0], rows[-1][key][1]
    if value < first_min:
        return Suggestion(sizes[0], f"Below the smallest size in the chart ({sizes[0]}).")
    if value >= last_max:
        return Suggestion(sizes[-1], f"Above the largest size in the chart ({sizes[-1]}).")

    index = next(i for i, row in enumerate(rows) if row[key][0] <= value < row[key][1])
    low, high = rows[index][key]
    position = (value - low) / (high - low)
    boundary = charts()["fit_preference"]["boundary_fraction"]
    if preference == "slim" and position < boundary and index > 0:
        return Suggestion(sizes[index - 1], f"Between {sizes[index - 1]} and {sizes[index]}.")
    if preference == "relaxed" and position >= 1 - boundary and index < len(rows) - 1:
        return Suggestion(sizes[index + 1], f"Between {sizes[index]} and {sizes[index + 1]}.")
    return Suggestion(sizes[index])


def suggest_top(chest_cm: float | None, preference: str) -> Suggestion | None:
    if chest_cm is None:
        return None
    return _pick(charts()["tops"]["sizes"], "chest_cm", chest_cm, preference)


def suggest_bottom(
    waist_cm: float | None, hip_cm: float | None, preference: str
) -> Suggestion | None:
    """The larger of the waist and hip sizes, so the trousers fit both."""
    rows = charts()["bottoms"]["sizes"]
    candidates = [
        _pick(rows, key, value, preference)
        for key, value in (("waist_cm", waist_cm), ("hip_cm", hip_cm))
        if value is not None
    ]
    if not candidates:
        return None
    order = [row["size"] for row in rows]
    return max(candidates, key=lambda s: order.index(s.size))
