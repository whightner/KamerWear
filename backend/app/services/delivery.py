"""Demo delivery-fee rule (not a logistics engine).

A flat fee per destination city, calculated by the server only:

    Douala     1 500 FCFA
    Yaoundé    2 000 FCFA
    Bafoussam  2 500 FCFA
    elsewhere  3 500 FCFA

City names are compared without accents or case ("yaounde" = "Yaoundé").
"""

import unicodedata

DEFAULT_DELIVERY_FEE = 3500
CITY_DELIVERY_FEES = {
    "douala": 1500,
    "yaounde": 2000,
    "bafoussam": 2500,
}


def _normalise(city: str) -> str:
    decomposed = unicodedata.normalize("NFKD", city.strip().lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def delivery_fee(city: str) -> int:
    return CITY_DELIVERY_FEES.get(_normalise(city), DEFAULT_DELIVERY_FEE)
