# Smart Document & Form Intelligence System

Processes invoices, receipts, forms and certificates: preprocessing → OCR/layout → classification → field & table extraction → validation → structured, searchable storage.

```
Upload → Preprocess → OCR → Classify → Extract → Validate → Store → Search / API
```

## Team ownership

| Area | Owner | Code | Branch prefix |
|---|---|---|---|
| Preprocessing + OCR | Person A | `src/docint/preprocessing`, `src/docint/ocr` | `feature/preprocess-*`, `feature/ocr-*` |
| Classification + layout | Person B | `src/docint/classifier` | `feature/classifier-*` |
| Extraction + validation | Person C | `src/docint/extraction`, `src/docint/validation` | `feature/extract-*`, `feature/validation-*` |
| API + DB + UI | Person D | `src/docint/api`, `src/docint/db` | `feature/api-*`, `feature/db-*`, `feature/ui-*` |
| Architecture, integration, evaluation | Lead | `src/docint/pipeline.py`, `docs/` | `feature/pipeline-*` |

(Replace "Person A-D" with real names.)

## Quick start

```bash
git clone <repo-url> && cd doc-intelligence
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest                              # should pass out of the box
uvicorn docint.api.main:app --reload --app-dir src
```

Open http://127.0.0.1:8000/docs and try `POST /documents` with any file. The stages are stubs right now, so you get dummy JSON back. Each owner replaces their stub with a real implementation.

Heavy ML/OCR packages are separate: `pip install -r requirements-ml.txt` (only if your module needs them). Tesseract also needs its system binary installed.

## Rules

1. `src/docint/schemas.py` is the contract. Don't change it without telling everyone (see `docs/schema.md`).
2. Don't change another person's function signature. Add optional parameters instead.
3. Never push to `main`. Use a branch and a PR (see `CONTRIBUTING.md`).
4. `pytest` must pass before you open a PR.
