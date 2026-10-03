"""Check Smart Fit with the real pose model on your own licensed photos.

    python -m app.ai.evaluate_smart_fit --height 175 front.jpg [more_front.jpg ...]
    python -m app.ai.evaluate_smart_fit --height 175 --side side.jpg front.jpg

For each photo it runs the same checks and estimate as the API, on the
original and on transformed copies (smaller, heavy JPEG, a slight crop, a
mirror image), and reports the measurements, suggested sizes, confidence and
how much they move between copies. Photos are only read, never copied or
stored. Uses no fake data: it fails if the model isn't available.

The typed height is an assumption for photos of people whose height you
don't know, so absolute numbers can't be checked this way; stability and
the photo checks can.
"""

import argparse
import io
import sys
import time
from pathlib import Path

from PIL import Image, ImageOps

from app.fit import charts, measure
from app.fit.pose import FitServiceUnavailable, get_backend
from app.services.fit import analysis_copy


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return Image.open(io.BytesIO(buffer.getvalue())).convert("RGB")


TRANSFORMS = {
    "original": lambda im: im,
    "half size": lambda im: im.resize((im.width // 2, im.height // 2)),
    "JPEG quality 30": lambda im: _jpeg(im, 30),
    "crop 3% sides": lambda im: ImageOps.crop(im, border=(int(im.width * 0.03), 0)),
    "mirrored": ImageOps.mirror,
}
KEYS = ("shoulder_width_cm", "chest_cm", "waist_cm", "hip_cm", "inseam_cm")


def _view(backend, image: Image.Image, name: str) -> measure.View:
    warnings = measure.check_image(image, name)
    view = measure.check_pose(backend.detect(analysis_copy(image)), name)
    view.warnings = warnings + view.warnings
    return view


def evaluate(backend, front_path: Path, side_path: Path | None, height: int) -> None:
    print(f"\n== {front_path.name}" + (f" + side {side_path.name}" if side_path else ""))
    front_image = Image.open(front_path).convert("RGB")
    side_image = Image.open(side_path).convert("RGB") if side_path else None
    results = {}
    for label, transform in TRANSFORMS.items():
        started = time.monotonic()
        try:
            front = _view(backend, transform(front_image), "front")
            side = _view(backend, transform(side_image), "side") if side_image else None
        except measure.FitPhotoError as exc:
            print(f"  {label:18s} REJECTED {exc.photo}: {exc.code}: {exc.message}")
            continue
        body = measure.estimate(front, side, height)
        m = body.measurements
        top = charts.suggest_top(m["chest_cm"], "regular")
        bottom = charts.suggest_bottom(m["waist_cm"], m["hip_cm"], "regular")
        results[label] = (m, top.size if top else None, bottom.size if bottom else None)
        values = " ".join(f"{k.split('_')[0]}={m[k]}" for k in KEYS)
        print(
            f"  {label:18s} {values} | top={results[label][1]} trousers={results[label][2]} "
            f"| {body.confidence} | {len(body.warnings)} warning(s) "
            f"| {(time.monotonic() - started) * 1000:.0f} ms"
        )
        for warning in body.warnings if label == "original" else []:
            print(f"      - {warning}")
    if len(results) > 1:
        spread = []
        for key in KEYS:
            values = [r[0][key] for r in results.values() if r[0][key] is not None]
            if len(values) > 1:
                spread.append(f"{key.split('_')[0]} ±{(max(values) - min(values)) / 2:.1f}")
        tops = {r[1] for r in results.values()}
        bottoms = {r[2] for r in results.values()}
        print(f"  spread: {', '.join(spread) or 'n/a'}; tops {tops}; trousers {bottoms}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate Smart Fit on real photos.")
    parser.add_argument("photos", nargs="+", type=Path, help="front photos")
    parser.add_argument("--side", type=Path, help="side photo used with every front photo")
    parser.add_argument("--height", type=int, default=175, help="assumed height in cm")
    args = parser.parse_args(argv)
    try:
        backend = get_backend()
    except FitServiceUnavailable as exc:
        print(f"Model unavailable, nothing evaluated: {exc}", file=sys.stderr)
        return 1
    print(f"Model {backend.model_name}, assumed height {args.height} cm")
    for photo in args.photos:
        evaluate(backend, photo, args.side, args.height)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
