# Investor Memory

Memory system for investor workflows: ingest emails, meeting notes, and documents, extract entities (companies/people), and search via semantic similarity.

## Setup

Requires **Python 3.12** (onnxruntime does not yet support 3.13).

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Run

```bash
source .venv/bin/activate
uvicorn src.api.routes:app --host 0.0.0.0 --port 8000
```

The app will be available at http://localhost:8000.

- **UI**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health

## Seed data

Once the server is running, seed the database with synthetic data:

```bash
curl -X POST http://localhost:8000/admin/seed
```

## Tests

```bash
source .venv/bin/activate
pytest
```
