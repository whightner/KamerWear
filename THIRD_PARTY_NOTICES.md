# Third-Party Notices

The MIT License in this repository applies to **original KamerWear source code** unless a file states otherwise. It does not replace the licenses, model cards, copyright notices or terms of third-party dependencies and assets.

## Demo imagery

Bundled storefront/demo images have their own source and license information:

- [frontend/public/images/CREDITS.md](frontend/public/images/CREDITS.md)

Do not assume those images are covered by KamerWear's MIT License.

## Smart Fit

Smart Fit uses a pretrained MediaPipe Pose Landmarker model. Model/package licensing and attribution are documented in:

- [docs/architecture/smart-fit.md](docs/architecture/smart-fit.md)

Downloaded model files are intentionally excluded from Git.

## Visual Search

Visual Search is designed around OpenCLIP and pretrained model weights. Relevant model attribution, preparation and limitations are documented in:

- [docs/architecture/visual-search.md](docs/architecture/visual-search.md)

Model weights are not distributed by this repository and may be subject to their own model-card/license terms.

## Libraries

JavaScript and Python dependencies remain under their respective licenses. See:

- `frontend/package.json`
- `backend/requirements.txt`
- `backend/requirements-smart-fit.txt`
- `backend/requirements-visual-search.txt`

When redistributing KamerWear, review the notices/terms of any dependencies, models and assets you redistribute with it.
