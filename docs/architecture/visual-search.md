# Visual search

Customers upload (or take) a photo of shoes, clothes or a bag and get the
KamerWear products that look most similar. Product pages also show
**visually similar** items. Both use a pretrained image model; KamerWear did
not create or train it.

```
customer photo ──► pretrained vision encoder ──► 512-number embedding ─┐
                                                                       ├─► cosine similarity
catalog photos ──► same encoder (indexed in advance) ──► embeddings ──┘          │
                                                                                 ▼
                                        best photo per product ─► type guard ─► ranked products
```

## For the presentation (short explanation)

> KamerWear converts both catalog images and the customer's uploaded image
> into numerical feature vectors (embeddings) using a pretrained vision model,
> OpenCLIP ViT-B-32. It compares these vectors with cosine similarity and
> returns the closest fashion items. The same model also compares the photo
> with short descriptions such as "a photo of a sneaker"; when one type is
> clearly most likely, products of that type are shown first, which prevents
> obviously unrelated results. KamerWear did not train the model: it uses it to
> extract features and adds its own catalog search and ranking logic.

## What it does

- Encodes every photo of active products once (the **index**) and stores the
  embeddings in PostgreSQL.
- Encodes the customer's photo at search time, compares it with all indexed
  photos (cosine similarity of L2-normalised vectors), keeps each product's
  **best-matching photo**, and returns each product once.
- Applies a **type guard**: zero-shot comparison of the photo with text
  prompts per type group (footwear, bags, hoodies/sweatshirts/jackets,
  t-shirts/shirts, trousers, plus an "other" group for non-fashion photos).
  If one group gets at least half of the softmax weight and it isn't "other",
  products of that group are listed first, ordered by visual similarity;
  remaining products follow under "Other visually similar items". Otherwise
  results are ordered by visual similarity alone. The guard only reorders: it
  never adds products that don't look similar, and product names, keywords or
  file names never influence the score.
- **Find Similar** on a product page averages that product's own stored photo
  embeddings into one query vector, excludes the product, and lists products
  of the same catalog type first. It needs no model inference at request time.
  The older rule-based list is still shown separately as **Related products**.

## What it does not do

- It does not identify brands or guarantee the identical product; it finds
  similar-looking items in this catalog.
- Scores are cosine similarities used for ranking, not probabilities. The UI
  never shows them as percentages or "accuracy". When even the best score is
  low (below 0.55, a heuristic), the page says "These are the closest products
  currently available."
- It never trains on customer photos and never keeps them (see Privacy).
- If the model can't be loaded, it answers `visual_search_unavailable`. It
  never falls back to category rules while calling the results visual search.

## Model

| | |
| --- | --- |
| Model | OpenCLIP **ViT-B-32**, weights `laion2b_s34b_b79k` (trained by LAION on LAION-2B) |
| Library | [open_clip](https://github.com/mlfoundations/open_clip) 3.x (MIT licence) on PyTorch 2.9+ (BSD-style licence) |
| Weights | Hugging Face `laion/CLIP-ViT-B-32-laion2B-s34B-b79K`, MIT licence per its model card (please re-check the card when downloading); the card describes the model as intended for research, which fits this academic demo |
| Embedding size | 512 numbers (float32), L2-normalised |
| Size | ~151 M parameters, ~600 MB of weights |
| Why | Maintained, widely used CLIP model; works for both image-image similarity and zero-shot type prompts; runs on CPU; permissive licence; wheels for Python 3.14 (torch 2.14.1 and open_clip 3.3.0 verified on Python 3.14.8) |

Attribution: *OpenCLIP by Ilharco et al. (2021); CLIP by Radford et al.
(OpenAI, 2021); weights trained by LAION on the LAION-2B dataset.* The
training data comes from the public web and carries its biases.

Configuration (environment or `backend/.env`):
`VISUAL_SEARCH_MODEL`, `VISUAL_SEARCH_PRETRAINED`,
`VISUAL_SEARCH_IMAGE_ROOT` (folder containing `images/products/`, default
`../frontend/public`), `VISUAL_SEARCH_CACHE_DIR` (default
`backend/.model-cache`, git-ignored) and `VISUAL_SEARCH_OFFLINE`.

## Setup and demo preparation

The ML packages are optional so the shop runs without them:

```bash
cd backend
pip install -r requirements.txt
pip install -r requirements-visual-search.txt   # torch, torchvision, open_clip
# CPU-only machines can install the smaller CPU build of torch first:
#   pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

python -m app.ai.prepare_visual_search    # downloads ~600 MB into backend/.model-cache, self-test
python -m app.ai.visual_search_index      # encodes the catalog photos
python -m app.ai.evaluate_visual_search   # optional: real searches with transformed photos
```

**Before a presentation** (no network needed afterwards):

1. Run the three commands above with internet access.
2. Set `VISUAL_SEARCH_OFFLINE=true` in `backend/.env`, so the API never tries
   to download.
3. Verify offline: `python -m app.ai.prepare_visual_search --offline` must
   print "Ready", and **Admin → Visual search** must show "Ready" with all
   photos indexed.

The downloaded weights live in `backend/.model-cache/` and are never committed.

## Index

`python -m app.ai.visual_search_index` (or **Admin → Visual search → Update
visual index**):

1. loads the model (once per process);
2. lists the photos of active products in active categories;
3. resolves each path safely under `VISUAL_SEARCH_IMAGE_ROOT/images/products/`
   (no `..`, absolute paths or URLs), hashing the file;
4. skips photos whose path, file content (SHA-256) and model are unchanged;
5. encodes the rest in batches of 16 and updates rows in place (unique per
   photo and model, so re-runs never duplicate);
6. deletes rows of inactive/deleted photos and of other models;
7. reports indexed / unchanged / failed / removed and logs the run.

Only one build runs at a time (PostgreSQL advisory lock); a second one gets
`index_busy`. Photos added or changed in the admin are **not searchable until
the index is updated**: the admin status page lists them as "Not indexed yet"
or "Changed since indexing", and the product editor marks them.

**Storage choice.** Embeddings are float32 bytes in
`product_image_embeddings` (2 KB per photo). With ~70 photos the search loads
them (~140 KB) and computes all similarities with one NumPy matrix product in
well under a millisecond, so pgvector or an external vector database would add
setup without benefit. pgvector also wasn't verified with this PostgreSQL 18
build. Beyond tens of thousands of photos, an approximate index (e.g. pgvector
HNSW) would be the next step.

## API

| Endpoint | Who | Purpose |
| --- | --- | --- |
| `POST /api/v1/visual-search?limit=8` | public | multipart `image`; `limit` 1–24 |
| `GET /api/v1/products/{slug}/visual-similar?limit=4` | public | visually similar products (1–12) |
| `GET /api/v1/admin/visual-search/status` | ADMIN | model, ready, indexed/stale/unindexed/missing photos, last run |
| `POST /api/v1/admin/visual-search/rebuild` | ADMIN | update the index (`index_busy` if running) |

Response items contain the normal product card data, `similarity_score`,
`matched_image` and `matches_predicted_type`. Embeddings are never returned.

Errors: `invalid_image` (400), `image_too_large` (413), `unsupported_image_type`
(415), `too_many_searches` (429), `visual_search_unavailable` (503),
`visual_search_not_ready` (503), `no_searchable_products` (404),
`product_not_indexed` (409). Model errors are logged for developers; customers
only get the generic message.

## Upload security and privacy

- **Uploads only.** The endpoint never fetches URLs.
- **Size.** Bodies over 8 MB (+ multipart overhead) are refused before
  parsing, by both Next.js and FastAPI.
- **Content, not extension.** Pillow must recognise JPEG, PNG or WebP.
  Anything else, including text renamed `.jpg`, is refused. HEIC isn't
  supported yet (`unsupported_image_type`).
- **Dimensions.** At most 8 000 px per side and 30 megapixels, checked before
  decoding. Pillow's decompression-bomb protection is tightened, and its
  warnings are treated as errors.
- **Rate limit.** 12 searches per minute per client IP. The limiter is
  in-memory, per API process (fine for the single-process MVP).
- **No retention.** The photo is decoded in memory. Starlette may spool a
  large upload to a temporary file, which is closed and deleted before the
  search runs. The photo is never written to the database, `public/`, logs or
  Git. The decoded copy is rebuilt from pixels only, so EXIF data (including
  GPS location) is dropped. The phone's rotation is applied first.
- The browser keeps the last **results** (not the photo) in `sessionStorage`
  so "back" from a product page shows them again.

## Performance (measured in the development container)

4 CPU cores, no GPU, PyTorch 2.14.1 CPU inference. Measured with the real
ViT-B-32 architecture; random weights were used for timing only because the
pretrained download was blocked there (same compute cost):

| Step | Time |
| --- | --- |
| Encode one photo (batched) | ~32 ms |
| Index 71 catalog photos | ~3.5 s |
| Type-guard prompts (first search only, then cached) | ~0.4 s |
| One search (decode, encode, guard, rank, load products) | ~90 ms |
| Model load (random init; real weights add reading ~600 MB) | ~1.4 s |

These are indications, not guarantees; a laptop will differ.

## Status of validation

- **Automated tests (41 + 2):** a deterministic fake encoder checks upload
  validation, index (re-runs, missing files, stale photos, inactive products,
  unsafe paths, locking), ranking, per-product aggregation, the type guard,
  product similarity, errors (no fallback), rate limiting, privacy and admin
  authorisation. An optional test runs the real OpenCLIP adapter (random
  weights) to check preprocessing, 512-d normalised output and CPU speed.
- **Real-model quality check: still pending (re-attempted 2026-10-04, Task 012).**
  `huggingface.co` (and `download.pytorch.org`) were still blocked by the
  development environment's network policy (proxy answered 403), so the
  pretrained ViT-B-32 / laion2b_s34b_b79k weights could not be downloaded and
  no real search could be run. What *is* verified: the architecture, the UI
  and API flows, the index logic and ranking with the deterministic test
  encoder, the real OpenCLIP model architecture with random weights (shape,
  normalisation, CPU timing), and the unavailable/fail-closed behaviour.
  No result quality is claimed. On a machine with internet access run:

  ```bash
  pip install -r requirements-visual-search.txt
  python -m app.ai.prepare_visual_search
  python -m app.ai.visual_search_index
  python -m app.ai.evaluate_visual_search   # sneaker, hoodie, bag, trousers, tee; resize, crop, JPEG, padded screenshot
  ```

  and record, for each query, the top 5 products, the predicted type, the
  search time and whether the expected type appears near the top. The type
  guard threshold (0.5) and the weak-match threshold (0.55) are untuned
  heuristics until then.

## Limitations

- Needs the ~600 MB model and its preparation step; without it, visual search
  is clearly unavailable (the rest of the shop is unaffected).
- Similarity reflects the photo (colour, shape, background), so studio photos
  and real-life snapshots can rank differently; brands aren't recognised.
- The type-guard threshold and the "weak match" score are heuristics to tune
  with the real model.
- In-memory rate limiting and the model live in one API process; several
  workers would each load the model (~600 MB RAM each).
- New admin photos need an index update before they're searchable.
