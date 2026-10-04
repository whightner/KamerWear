# Smart Fit

Smart Fit suggests clothing sizes from the customer's height and one or two
guided photos. It gives **estimates to help choose a size**, not exact body
measurements. The customer always reviews and confirms the result before
anything becomes their Fit Profile.

```
height (typed) ─┐
front photo ────┼─► pretrained pose model ─► 33 body landmarks + body outline (mask)
side photo  ────┘      (MediaPipe, CPU)                │
  (optional)                                           ▼
                        KamerWear geometry: scale by height, widths/depths,
                        ellipse circumference, photo checks, confidence
                                                       │
                                                       ▼
                      size charts (JSON) + fit preference ─► suggested sizes
                                                       │
                                                       ▼
                       customer reviews, corrects, confirms ─► Fit Profile
                                                       │
                                                       ▼
                       product page: "Recommended size for you: M"
```

## For the presentation (short explanation)

> The customer types their height and takes a front photo and, ideally, a side
> photo. A pretrained pose model from Google (MediaPipe Pose Landmarker; we did
> not train it) finds 33 body points and the outline of the person. Because we
> know the person's real height, we can convert pixels to centimetres. From the
> outline we measure the body's width at chest, waist and hip level on the
> front photo and its depth on the side photo, and approximate each
> circumference as an ellipse. Those approximate dimensions are compared with
> KamerWear's demo size charts to suggest a top size and a trouser size. We
> also give a confidence level (high, medium or low), which says how well the
> photos supported the estimate; it is not an accuracy percentage. The customer
> checks and corrects the sizes, and only what they confirm is saved. Shoe
> sizes are never estimated from photos: the customer enters them. Photos are
> analysed in memory and discarded; we keep only the numbers.

What we do **not** claim: that the system scans the body or knows the exact
size. It is an approximation from two 2D photos, and it is sensitive to
clothing, pose and camera angle. Its real-world accuracy has not been
validated (see [Ground truth](#ground-truth)).

## User flow

1. `/fit`. Visitors see the explanation and the privacy notes and must log in
   or register to start (`/login?next=/fit`, `/register?next=/fit`).
2. **Height** (required, 100–230 cm), optional **EU shoe size** (typed by the
   customer), and **fit preference** (Slim / Regular / Relaxed).
3. **Front photo** with written instructions: whole body in frame, standing
   straight and facing the camera, arms slightly away from the body, everyday
   clothes that follow the body's shape (no big coat or bag), good light,
   camera level, only one person in the photo.
4. **Side photo** (optional, recommended): whole body side-on, arms relaxed by
   the sides, same place and camera position. The page says clearly that
   without it the estimate always has **low** confidence.
5. **Estimate** (`POST /api/v1/fit/estimate`). Photo problems send the customer
   back to that photo's step with a specific message (e.g. "Your feet aren't
   fully visible in the front photo…").
6. **Review**: confidence and its reasons, tips to improve, approximate
   dimensions (whole cm, marked ≈), and editable size fields prefilled with the
   suggestions. Changing the fit preference updates the suggestions (they are
   returned for all three preferences) until the customer picks a size
   themselves.
7. **Save my Fit Profile** (`PUT /api/v1/fit/profile`). Only now is the profile
   created or replaced. Redirects to `/account/fit-profile`.
8. **Product pages** for Smart Fit products show the confirmed size.

`/account/fit-profile` shows the confirmed sizes, height, preference, source
(estimated, estimated then adjusted, or entered manually), confidence, last
update and the estimated dimensions, with **Edit sizes**, **Rescan with new
photos** and **Delete Fit Profile** (asks for confirmation; the account stays).
Without a profile it offers the photo flow or a manual form. The account
dashboard tile and the footer "Fit Profile" link go there; the homepage
"Create My Fit Profile" button opens `/fit`.

## Model

| | |
| --- | --- |
| Model | MediaPipe **Pose Landmarker (heavy)**, float16, version 1 (BlazePose GHUM 3D) by Google |
| File | `pose_landmarker_heavy.task`, 30.7 MB, pinned URL on `storage.googleapis.com/mediapipe-models/…` and SHA-256 `64437af8…cbc7b` (checked on download and on every load) |
| Library | `mediapipe` 1.0.1 (Apache-2.0), pulls in OpenCV contrib (Apache-2.0), NumPy, matplotlib, absl, flatbuffers, sounddevice |
| Licence | Model card: Apache License 2.0. Its intended use is pose estimation for applications such as fitness and entertainment, not life-critical decisions. Fairness was evaluated across 14 geographic subregions; trained on images including consented captures. |
| Output used | 33 landmarks (x, y, visibility) and the person-segmentation mask; raw tensors are never returned by the API |
| Python | Verified on Python 3.14.8 (wheel `mediapipe-1.0.1`, Linux x86-64) |
| Hardware | CPU only, no GPU needed: ~0.7–1 s to load, ~100–120 ms per photo (4-core container), ~370 MB peak process memory |
| Linux note | Needs the EGL/GLES runtime (`apt-get install libegl1 libgles2`), otherwise import fails with `libEGL.so.1` missing |
| Training | None. KamerWear does not train or fine-tune anything, and never on customer photos |

Why this model: maintained by Google, permissive licence, one small file,
CPU-friendly, offline after one download, and it provides both landmarks and
a body outline (landmarks alone can't give widths). Paid APIs and separate
services were excluded by the project rules.

**Known library bug handled:** mediapipe 1.0.1 aborts the whole process when
it copies out the float mask of an image whose width is not row-aligned
(e.g. 925 px). The backend pads photos on the right to a multiple of 16 px
(edge pixels) and crops the mask back; tested in `test_fit_mediapipe.py`.

### Setup and demo preparation

```bash
cd backend
pip install -r requirements-smart-fit.txt
python -m app.ai.prepare_smart_fit            # download (once) + SHA-256 check + self-test
python -m app.ai.prepare_smart_fit --offline  # before a demo: local file only, no network
```

The model goes to `SMART_FIT_MODEL_PATH` (default
`backend/.model-cache/smart-fit/pose_landmarker_heavy.task`, git-ignored). The
API itself **never downloads**: if the file is missing or doesn't match the
pinned hash, photo estimates answer `503 fit_service_unavailable` and the page
offers manual size entry. There is no fake fallback: the API never invents
"M / 32 / EU 43" and calls it AI. Saved profiles, manual sizes and product
recommendations keep working without the model.

The self-test analyses `frontend/public/images/features/smart-fit.webp` (a
licensed full-body photo already in the repo) and must find a full body.

## What happens to the data

| Data | Where it goes | Kept? |
| --- | --- | --- |
| Photos (front, side) | Browser → Next.js route handler `/api/fit/estimate` (in memory) → FastAPI | **No.** Decoded in memory, analysed, closed. Never written to PostgreSQL, `public/`, logs, Git or a backend folder. |
| Temporary upload files | Starlette may spool uploads over 1 MB to an anonymous temp file | Closed (deleted) right after reading, before analysis (`form.close()`). A test checks the temp folder is empty afterwards. |
| EXIF (GPS, device, time) | Dropped: the image is rebuilt from pixels only, after applying the phone's rotation | No. A test uploads a JPEG with GPS/camera EXIF and checks the analysed image has none. |
| Landmarks / mask | Process memory during the request | No. Never returned or logged. |
| Estimate (`fit_estimates`) | Derived numbers only: height, preference, estimated dimensions, suggested sizes, confidence, warnings, version | The **last 3** per customer, for review and confirmation. Deleted with the profile. |
| Fit Profile (`fit_profiles`) | What the customer confirmed | Until edited or deleted. |
| Logs | Estimate id and confidence level | No measurements, file names or image bytes. |

KamerWear does not train any model on customer photos, does no face or
identity recognition, and does not infer age, weight, health, race or gender
identity. The instructions never ask for revealing clothing: everyday clothes
that follow the body's shape are enough (and loose clothing simply makes the
estimate less precise, which the result explains).

## Photo checks

Before the model: JPEG/PNG/WebP judged by content (HEIC refused), ≤ 8 MB per
photo, ≤ 8 000 px per side and 30 MP, decompression-bomb protection (same
loader as visual search), shorter side ≥ 400 px, not too dark (mean grey ≥ 40).
A blurry photo (low Laplacian variance) gives a warning.

From the model's output:

| Check | Result |
| --- | --- |
| Nobody detected | `422 fit_pose_not_detected` |
| More than one clearly visible person | `422 fit_multiple_people` |
| Head, shoulders/hips or ankles/feet not visible or outside the frame; head touching the top edge | `422 fit_full_body_not_visible` with a specific message |
| Person smaller than 30 % of the photo height | `422 fit_photo_quality` ("move closer"); < 50 % is a warning |
| Front photo looks like a side view (shoulder spread < 0.40 × torso length) | `422 fit_photo_quality`; < 0.50 is a warning |
| Side photo looks like a front view (spread > 0.45) | `422 fit_photo_quality` for the side photo |
| Key landmarks with low visibility | warning |

Every error names the photo (`"photo": "front"` or `"side"`), so the page
returns to that step. We don't claim checks the model can't support (e.g. we
can't tell whether two photos show the same person, and we deliberately don't
try).

## Measurement method

All in `backend/app/fit/measure.py`.

1. **Scale.** Top of the head = first mask row above the nose, near the head;
   floor = lowest heel/toe landmark (extended to the mask's bottom by at most
   2.5 % of the body height for soles). `cm_per_px = height_cm / (floor − top)`.
   Each photo uses its own scale.
2. **Levels** are placed between the shoulder line (S) and the hip-landmark line
   (H): chest at S + 0.30 (S→H), waist = narrowest width between 0.50 and 0.80,
   hips = widest width between 0.95 and 1.35.
3. **Width** (front) = the mask's continuous run through the body's centre line
   at that level. If an arm or hand (shoulder → elbow → wrist → fingers) lies
   inside that run, the arm touches the body there and the width would include
   it, so that level is **not estimated** (warning: hold your arms slightly
   away). A chest width over 1.6 × the shoulder-joint distance is treated the
   same way.
4. **Depth** (side) = the run at the same relative levels on the side photo.
   A depth outside 45–105 % of the width is treated as unreliable and replaced
   by the typical ratio (warning).
5. **Circumference** = ellipse perimeter (Ramanujan:
   `π[3(a+b) − √((3a+b)(a+3b))]`, a = width/2, b = depth/2) × a fixed shape
   factor, because a torso cross-section is fuller than an ellipse
   (chest 1.15, waist 1.07, hips 1.06; approximate values chosen so the
   ellipse reproduces typical published adult averages such as ANSUR II).
   **Without a side photo**, depth = width × a typical ratio (chest 0.75,
   waist 0.77, hips 0.70) and the confidence is always low.
6. **Inseam** = crotch to floor. The crotch is where the gap between the legs
   starts on the centre line, if that is within 9 % of the body height below
   the hip landmarks; otherwise (loose trousers, shorts, legs together) it is
   placed 5 % of the body height below them, and the result says so.
7. **Shoulder width** = distance between the shoulder joints (labelled
   "between shoulder joints", not a tailor's shoulder seam).
8. **Plausibility.** Values outside chest 65–160, waist 50–150, hips 65–160,
   inseam 50–100, shoulder 25–55 cm are dropped with a warning.
9. **Consistency.** If the hip height relative to body height differs by more
   than 0.05 between the front and side photos, a warning is added and
   confidence drops.

Values that can't be estimated stay **null**; nothing is filled in to look
complete.

## Confidence

A rule-based level, never a percentage and never called accuracy:

```
score = mean visibility of key landmarks (nose, shoulders, hips, ankles; both photos)
        − 0.05 per warning − 0.10 per missing chest/waist/hip − 0.15 if photos disagree
high   : side photo used, score ≥ 0.80, nothing missing, no warnings
medium : side photo used, score ≥ 0.60
low    : otherwise, and always without a side photo
```

The response lists readable reasons (`confidence_factors`, e.g. "No side
photo: body depth was assumed from typical proportions, so confidence is
low.") and actionable `warnings`. High confidence means the photos were
clear and consistent, **not** that the size is guaranteed.

## Size charts

`backend/app/fit/size_charts.json`, version `kamerwear-demo-2026.1`, public at
`GET /api/v1/fit/size-charts`. **Generic demo charts** following common unisex
ready-to-wear ranges; not any brand's official chart. A size covers `[min, max)`
in cm.

| Tops (chest) | XS 80–88 · S 88–96 · M 96–104 · L 104–112 · XL 112–120 · XXL 120–128 |
| --- | --- |
| Trousers (waist / hips) | 28: 70–75 / 86–91 · 30: 75–80 / 91–96 · 32: 80–86 / 96–101 · 34: 86–92 / 101–106 · 36: 92–98 / 106–111 · 38: 98–104 / 111–116 · 40: 104–110 / 116–121 |
| Letter equivalent | 28 XS · 30 S · 32 M · 34 L · 36 XL · 38/40 XXL (for S/M/L trousers) |
| Shoes | EU 35–48, entered by the customer |

Trousers take the **larger** of the waist and hip sizes. Outside a chart the
nearest end size is used with a note ("Above the largest size in the chart").

**Fit preference** (`boundary_fraction` 0.25): Slim moves one size down when
the measurement is in the lowest quarter of its size's range; Relaxed moves
one size up in the highest quarter; Regular keeps the best match. Example:
chest 103 cm (top of M): Regular → M, Relaxed → L; chest 97 cm: Slim → S.

**Shoes:** never estimated from body photos. The customer types an EU size;
it is shown as "Confirmed shoe size".

## Fit Profile rules

- `PUT /fit/profile` is the only way to create or change it. With
  `estimate_id`, the estimated dimensions are **copied on the server from the
  customer's own stored estimate**; the request can't contain measurements
  (`extra="forbid"`). Another customer's estimate → `404 fit_estimate_not_found`;
  a different height than the estimate's → `422 fit_estimate_mismatch`.
- The sizes the customer saves always win. `source` records
  `photo_estimate` (saved as suggested), `photo_corrected` (changed by the
  customer) or `manual`.
- A new estimate never changes the saved profile by itself; a rescan only
  replaces it when the customer confirms again.
- Changing the height manually drops the photo-estimated dimensions (they were
  scaled to the old height) and marks the profile `manual`.
- `DELETE /fit/profile` deletes the profile and all stored estimates, not the
  account.

## Product recommendations

`GET /api/v1/products/{slug}/fit-recommendation` (signed in). Only for products
with `smart_fit = true`; the kind comes from the product type (the same groups
as visual search): T-shirts/shirts/hoodies/sweatshirts/jackets → top size,
trousers/joggers/jeans → trouser size (numeric if the product's sizes are
numeric, otherwise the letter equivalent), sneakers/shoes → confirmed shoe
size. Bags and other one-size items → `unsupported` (the block is hidden).

| Status | Shown on the product page |
| --- | --- |
| `recommended` | "Recommended size for you: M" + **Select recommended size M** |
| `unavailable` | "Your usual size is M, but M is unavailable. Closest available size: L." + optional "Select L instead" |
| `not_offered` | "This product doesn't come in your size (XXL). Closest available size: XL." |
| `missing_size` | "Add your shoe size to your Fit Profile…" |
| `no_profile` | "Create your Fit Profile…" → `/fit` |
| `unsupported` | nothing |

Signed-out visitors see "Log in to see the size recommended for you". If the
call fails, the block says the recommendation isn't available and shopping
continues normally. Smart Fit **never** selects a variant by itself, adds to
the cart or changes an order: the button only selects the size in the picker,
and only if that size is in stock for the chosen colour.

The seed marks one T-shirt (Core Heavy Tee) and two trousers (Everyday Cargo,
numeric 30–36; Core Joggers, S–XL) as Smart Fit products in addition to the
hoodies, jackets and sneakers, so all three kinds can be demonstrated. The old
`smart_fit_demo_size` catalog field is no longer used by the storefront.

## API summary

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| `POST` | `/api/v1/fit/estimate` | customer | multipart `front` (required), `side` (optional), `height_cm`, `fit_preference`; 10 per 10 minutes per user |
| `GET` | `/api/v1/fit/profile` | customer | `404 fit_profile_not_found` if none |
| `PUT` | `/api/v1/fit/profile` | customer | confirm or edit |
| `DELETE` | `/api/v1/fit/profile` | customer | `204` |
| `GET` | `/api/v1/fit/size-charts` | public | the demo charts |
| `GET` | `/api/v1/products/{slug}/fit-recommendation` | customer | see above |

Errors: `invalid_fit_image` 400, `fit_image_too_large` 413,
`fit_pose_not_detected` / `fit_full_body_not_visible` / `fit_multiple_people` /
`fit_photo_quality` / `invalid_fit_height` 422, `too_many_fit_estimates` 429,
`fit_service_unavailable` 503. The rate limit is in memory in the single API
process (like the other limits): it resets on restart and isn't shared
between workers.

The Next.js route handler forwards the photos with the access token from the
HttpOnly cookie. Route handlers skip the session-refresh proxy, so an almost
expired token gets `401 session_expired`; the page then calls a Server Action
(which goes through the proxy's single refresh) and retries once.

## Tests

- **Backend (pytest):** a deterministic fake pose backend (`tests/fit.py`)
  draws synthetic silhouettes with known pixel widths, so the real geometry is
  checked with exact numbers: height scaling, determinism, front-only vs
  front+side circumference, confidence levels, arms touching, legs together,
  implausible values, unusual side depth, front/side mismatch, every photo
  check; the API (access, ownership, valid/malformed/oversized/extreme images,
  decompression bomb, HEIC, no person, several people, missing landmarks,
  temp-file cleanup, EXIF removal, model unavailable, model crash, rate limit,
  last-3 retention, confirm/correct/manual/validate/height change/rescan/
  delete/cross-user isolation) and recommendations (tops, numeric and letter
  trousers, shoes, missing shoe size, unavailable size with nearest, size not
  made, unsupported, no cart change, disappearing after delete). Chart tests
  cover ranges, boundaries and preferences.
- **Optional real-model tests** (`test_fit_mediapipe.py`, skipped unless
  mediapipe and the prepared model are present): full body found on the repo
  photo, odd widths don't crash, empty photo → nobody.
- **Browser (Playwright, real model):** visitor → register → `/fit` → height
  validation → front photo (cropped catalog photo refused with the feet
  message, photo replaced) → front-only estimate (low confidence) → retake
  with side photo → review → preference switch → keyboard correction → save →
  account page → product recommendation and "Select recommended size" → shoe
  and trouser recommendations → manual edit → "size not made" message →
  delete → recommendation disappears; model unavailable (503) shows manual
  entry, no fake sizes. Responsive 1440/1024/768/390 and axe (WCAG 2 A/AA +
  best practice) on every step.

## Real-model evaluation

`python -m app.ai.evaluate_smart_fit --height 175 [--side side.jpg] front.jpg …`
runs the same checks and estimate on the original photo and on transformed
copies (half size, JPEG quality 30, 3 % crop, mirror) and prints the spread.
Run in the development container with the real heavy model on MIT-licensed
Sylius demo fixture photos (not committed) and the repo's `smart-fit.webp`,
assuming 175 cm because the people's real heights are unknown:

- **Landmark / full-body detection:** 215 fixture photos processed without a
  crash. Of 168 photos (167 clothing fixtures and `smart-fit.webp`; not all
  show a whole person): 57 usable as front photos; 105 correctly
  refused as not full body (feet or head cropped), 3 refused for size/angle,
  3 with no person found (product-only shots). All 6 catalog product photos
  tried were correctly refused (cropped or no person).
- **Arms rule:** in most fashion photos the arms rest on the body, so chest
  and waist were correctly left out with the "arms slightly away" warning
  rather than including the arms. One photo with arms away gave all values
  (chest ≈ 105, waist ≈ 97, hips ≈ 116 cm, inseam ≈ 79 cm at 175 cm).
- **Stability (resize / JPEG / crop / mirror):** dimensions moved by
  ±0.2–2 cm; inseam up to ±3 cm when the leg gap was found in one copy and not
  another. Sizes stayed the same except when a value sat on a chart boundary
  (chest 103–105 cm flips M/L; hips around 116 cm flips 38/40). Half-size
  copies of a 700 px photo were refused as too small (by design, < 400 px).
- **Front/side:** only 3 fixtures qualified as side views (true profiles or
  near-profiles); pairing them with a front photo of a different model gave
  medium confidence with an "unusual outline" warning at chest and waist.
  Same-person front/side pairs were not available.
- **Clothing:** loose shorts and oversized T-shirts widen the outline (hips
  ≈ 115–128 cm at an assumed 175 cm), which pushes trouser suggestions up.
  This is the main practical limitation and is why the result is reviewed.

### Ground truth

**Smart Fit is technically functional, but real-world measurement accuracy
has not yet been validated against ground-truth tape measurements.** No
consenting volunteer with tape-measured dimensions was available in the
development environment (checked again in the final QA task, 2026-10-04), and
the fixture photos have no known heights or measurements. No measurement
comparison is reported because none was made. Before relying on
the numbers, measure a few consenting volunteers (height, chest, waist, hips,
inseam with a tape), take the guided photos, compare, and record only the
differences (no photos or identifying details in the repository).

## Limitations

- Two 2D photos give approximate outlines: clothing, posture, hair, camera
  height and lens distortion all affect the result. It is not a body scanner
  and not equivalent to a tailor's tape.
- Arms must be away from the body on the front photo, or chest/waist/hips
  can't be estimated.
- The ellipse model, typical depth ratios, shape factors, crotch drop and
  thresholds are approximations; they were not tuned on measured people.
- The size charts are generic demo charts, and the same chart is used for
  every product.
- Front-only estimates are always low confidence.
- We can't verify that both photos show the same person (by design: no
  identity recognition).
- The model and the rate limit live in the single API process; several
  workers would each load the model (peak memory grew from ~50 MB to ~370 MB
  after loading it and analysing one photo).
- Visual search (Task 009) still needs its real-model quality check: the
  OpenCLIP weights couldn't be downloaded in the development container
  (Hugging Face was blocked). See [visual-search.md](visual-search.md).
