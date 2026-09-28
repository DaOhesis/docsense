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

---

## Docker (API + PostgreSQL)

> **Note for developers**: After pulling `feature/db-normalization`, delete your local `docint.db` before restarting the API. SQLAlchemy will recreate all tables automatically.

```bash
# Start API + PostgreSQL
docker compose up --build

# With the Streamlit review UI as well
docker compose --profile ui up --build
```

| Service | URL |
|---|---|
| FastAPI (Swagger) | http://localhost:8000/docs |
| Streamlit review UI | http://localhost:8501 |

```bash
# Tear down and wipe volumes (full reset)
docker compose down -v
```

**Customise credentials** by copying `.env.example` to `.env` and editing:

```env
POSTGRES_USER=myuser
POSTGRES_PASSWORD=secret
POSTGRES_DB=docint
```

---

## Streamlit review UI (local)

The review UI talks to the API over HTTP — it never imports the DB layer.

```bash
pip install -r requirements-ui.txt
streamlit run src/docint/ui/app.py
```

Set `API_URL` env var if the API is not on `http://localhost:8000`:

```bash
API_URL=http://api-host:8000 streamlit run src/docint/ui/app.py
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./docint.db` | SQLAlchemy database URL (SQLite or PostgreSQL) |
| `UPLOAD_DIR` | `./uploads` | Directory where uploaded files are stored |
| `API_URL` | `http://localhost:8000` | API base URL used by the Streamlit UI |
