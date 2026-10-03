"""Build or update the visual search index.

    python -m app.ai.visual_search_index           # new/changed images only
    python -m app.ai.visual_search_index --force   # re-encode everything

Loads the pretrained model, encodes the images of active products (resolved
safely under VISUAL_SEARCH_IMAGE_ROOT), updates rows in place and removes
obsolete ones. Prints indexed / unchanged / failed / removed counts.
"""

import argparse
import sys

from app.ai.encoder import EncoderUnavailable, get_encoder
from app.db.session import SessionLocal
from app.services.visual_search import IndexBusy, build_index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the KamerWear visual search index.")
    parser.add_argument("--force", action="store_true", help="re-encode unchanged images too")
    args = parser.parse_args(argv)
    try:
        encoder = get_encoder()
    except EncoderUnavailable as exc:
        print(f"Visual search model unavailable: {exc}", file=sys.stderr)
        return 1
    print(f"Model {encoder.model_name} ({encoder.dimensions} dimensions) loaded.")
    with SessionLocal() as db:
        try:
            report = build_index(db, encoder, trigger="cli", force=args.force)
        except IndexBusy as exc:
            print(str(exc), file=sys.stderr)
            return 1
    print(
        f"Indexed {report.indexed}, unchanged {report.unchanged}, failed {report.failed}, "
        f"removed {report.removed} in {report.seconds}s."
    )
    for problem in report.problems:
        print(f"  could not index {problem}", file=sys.stderr)
    return 0 if report.failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
