# Marksheet — AI answer sheet evaluation

Upload scanned handwritten answer pages → **Extract** (handwriting recognition) → **Structure** (split by question)
→ **Score** (rubric, by meaning) → **Flag confidence** (high / medium / low + reason) → review in the UI, export JSON/CSV.

## Stack
| Layer | Tech |
|---|---|
| Backend | Python 3.13, FastAPI, SQLite (SQLModel), background jobs with asyncio |
| AI | Google Gemini: vision models to read handwriting and grade, `gemini-embedding-2` for similarity. Backup models are tried automatically when one is busy |
| Images | PyMuPDF (PDF → images), OpenCV (straighten, contrast) |
| Frontend | React + Vite + TypeScript, hand-written CSS (~78 KB gzipped) |

> **New laptop?** Follow [SETUP.md](SETUP.md): install Python + Node.js, double-click `setup.bat`, then `run.bat`.

## Install (once)
```powershell
# backend
cd backend
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env        # then paste your key from https://aistudio.google.com/apikey
# frontend
cd ..\frontend
npm install
```

## Run
```powershell
.\run.ps1          # everything on http://localhost:8000 (builds the UI the first time)
.\run.ps1 -Dev     # hot reload: API :8000 + UI http://localhost:5173
```
Manual equivalent:
```powershell
cd backend;  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
cd frontend; npm run dev
```

### Command line (writes the deliverable files)
```powershell
cd backend
.\.venv\Scripts\python.exe cli.py ..\data\samples --rubric ..\data\rubrics\python_rubric.json
# -> outputs\results.json, outputs\results.csv
```

## Layout
```
backend/app/
  pipeline/  preprocess.py → extract.py → segment.py → score.py → confidence.py   (runner.py orchestrates)
  llm/gemini.py   fallback chain, retries, JSON-schema output, embeddings
  api/            routes.py (REST), jobs.py (background evaluation)
  db.py           rubrics + evaluation history (SQLite: backend/storage/app.db)
  cache.py        SQLite cache: re-running the same page is instant
backend/cli.py    terminal runner
frontend/src/     pages (Home, EvaluationView, Rubrics, RubricEditor) + components
data/             question paper, rubric JSON, sample sheets, SOURCE.md
outputs/          results.json / results.csv
APPROACH.md       approach note
```

## API
| Method | Path | |
|---|---|---|
| GET | `/api/rubrics` · `/api/rubrics/{id}` | list / get |
| PUT · DELETE | `/api/rubrics/{id}` | save / delete |
| POST | `/api/evaluations` | multipart `rubric_id` + `files[]` → `{id}` (runs in background) |
| GET | `/api/evaluations` · `/api/evaluations/{id}` | history / status + result |
| GET | `/api/evaluations/{id}/export?fmt=json\|csv` | download |
| DELETE | `/api/evaluations/{id}` | delete |

Interactive docs: http://localhost:8000/docs

## Config (`backend/.env`)
`PRIMARY_MODELS` and `CROSSCHECK_MODELS` are comma-separated lists of backup models, tried in order.
Other settings: `EMBED_MODEL`, and `JUDGE_RUNS` (number of grading runs, default 3).
