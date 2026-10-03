"""Product-type guard for visual search (zero-shot, no extra training).

The same CLIP model compares the query image with short text prompts such as
"a photo of a sneaker". The best-matching group is a ranking signal: when it
is clearly ahead, products of that group are listed first. CLIP scores are not
calibrated probabilities, so the threshold is a heuristic and the UI never
shows them as a percentage.
"""

from dataclasses import dataclass

import numpy as np

from app.ai.encoder import ImageEncoder

# Group -> (label shown to customers, prompts). "other" absorbs non-fashion
# photos so the guard isn't forced to pick a clothing type.
TYPE_GROUPS: dict[str, tuple[str, list[str]]] = {
    "footwear": (
        "Shoes",
        ["a photo of a sneaker", "a photo of a shoe", "a photo of sandals", "a photo of boots"],
    ),
    "bags": (
        "Bags",
        [
            "a photo of a bag",
            "a photo of a handbag",
            "a photo of a backpack",
            "a photo of a tote bag",
        ],
    ),
    "outerwear": (
        "Hoodies, sweatshirts & jackets",
        [
            "a photo of a hoodie",
            "a photo of a sweatshirt",
            "a photo of a jacket",
            "a photo of a puffer jacket",
        ],
    ),
    "tops": (
        "T-shirts & shirts",
        ["a photo of a t-shirt", "a photo of a shirt", "a photo of a polo shirt"],
    ),
    "bottoms": (
        "Trousers",
        ["a photo of trousers", "a photo of jeans", "a photo of shorts", "a photo of cargo pants"],
    ),
    "other": (
        "Other",
        [
            "a photo of a person's face",
            "a photo of a landscape",
            "a photo of food",
            "a photo of a room",
        ],
    ),
}

# Catalog product_type (lower case) -> group. Unknown types fall back to the category.
PRODUCT_TYPE_GROUPS = {
    "sneakers": "footwear",
    "shoes": "footwear",
    "sandals": "footwear",
    "boots": "footwear",
    "bag": "bags",
    "backpack": "bags",
    "tote": "bags",
    "hoodie": "outerwear",
    "sweatshirt": "outerwear",
    "jacket": "outerwear",
    "puffer": "outerwear",
    "t-shirt": "tops",
    "shirt": "tops",
    "polo": "tops",
    "trousers": "bottoms",
    "jeans": "bottoms",
    "shorts": "bottoms",
    "joggers": "bottoms",
}
CATEGORY_GROUPS = {"shoes": "footwear"}

# The winning group must reach this share of the softmax over all prompts.
CONFIDENCE_THRESHOLD = 0.5
# CLIP's usual temperature for zero-shot classification.
LOGIT_SCALE = 100.0


def product_group(product_type: str, category_slug: str) -> str | None:
    return PRODUCT_TYPE_GROUPS.get(product_type.strip().lower()) or CATEGORY_GROUPS.get(
        category_slug
    )


@dataclass(frozen=True)
class TypePrediction:
    group: str | None  # None when not confident or "other"
    label: str | None
    top_group: str  # best group, even if not confident (debugging)
    score: float  # softmax share of the top group; not a calibrated probability


class TypeGuard:
    """Caches the prompt embeddings of one encoder."""

    def __init__(self, encoder: ImageEncoder) -> None:
        self.model_name = encoder.model_name
        self._groups: list[str] = []
        prompts: list[str] = []
        for group, (_, group_prompts) in TYPE_GROUPS.items():
            for prompt in group_prompts:
                self._groups.append(group)
                prompts.append(prompt)
        self._text = encoder.encode_texts(prompts)

    def predict(self, image_embedding: np.ndarray) -> TypePrediction:
        logits = LOGIT_SCALE * (self._text @ image_embedding)
        weights = np.exp(logits - logits.max())
        weights /= weights.sum()
        shares: dict[str, float] = {}
        for group, weight in zip(self._groups, weights, strict=True):
            shares[group] = shares.get(group, 0.0) + float(weight)
        top = max(shares, key=shares.__getitem__)
        confident = shares[top] >= CONFIDENCE_THRESHOLD and top != "other"
        return TypePrediction(
            group=top if confident else None,
            label=TYPE_GROUPS[top][0] if confident else None,
            top_group=top,
            score=shares[top],
        )
