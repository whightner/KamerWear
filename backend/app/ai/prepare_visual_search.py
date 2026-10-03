"""Download (once) and verify the visual search model before a demo.

    python -m app.ai.prepare_visual_search            # download into the cache, then self-test
    python -m app.ai.prepare_visual_search --offline  # verify the cache works with no network

Afterwards set VISUAL_SEARCH_OFFLINE=true so the API never tries to download.
"""

import argparse
import os
import sys
import time

from PIL import Image

from app.core.config import settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prepare the visual search model.")
    parser.add_argument("--offline", action="store_true", help="use the cache only")
    args = parser.parse_args(argv)
    if args.offline:
        settings.visual_search_offline = True
        os.environ["HF_HUB_OFFLINE"] = "1"

    from app.ai.encoder import EncoderUnavailable, get_encoder

    cache = settings.visual_search_cache_dir
    print(f"Model: {settings.visual_search_model} / {settings.visual_search_pretrained}")
    print(f"Cache: {cache}")
    started = time.monotonic()
    try:
        encoder = get_encoder()
    except EncoderUnavailable as exc:
        print(f"Not ready: {exc}", file=sys.stderr)
        if exc.__cause__ is not None:
            print(f"  cause: {type(exc.__cause__).__name__}: {exc.__cause__}", file=sys.stderr)
        return 1
    loaded = time.monotonic() - started
    probe = Image.new("RGB", (224, 224), (180, 60, 40))
    started = time.monotonic()
    vector = encoder.encode_images([probe])[0]
    encoded = time.monotonic() - started
    print(
        f"Ready: loaded in {loaded:.1f}s, one image encoded in {encoded * 1000:.0f} ms, "
        f"{vector.shape[0]} dimensions."
    )
    print("Next: python -m app.ai.visual_search_index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
