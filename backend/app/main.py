"""FastAPI entrypoint.  Dev: uvicorn app.main:app --reload --port 8000
If frontend/dist exists (npm run build), the UI is served from the same process at http://localhost:8000."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import db
from app.api.routes import router
from app.config import PROJECT_DIR, get_settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    # Evaluations interrupted by a server restart would otherwise spin forever in the UI.
    from sqlmodel import select
    with db.session() as s:
        for row in s.exec(select(db.EvaluationRow).where(db.EvaluationRow.status.in_(["queued", "running"]))):
            row.status, row.error = "error", "Interrupted by server restart — please re-run."
            s.add(row)
        s.commit()
    yield


app = FastAPI(title="Answer Sheet Evaluator", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router)
# Only page images are public — never the storage root (it holds the SQLite files).
EVALS_DIR = get_settings().storage_dir / "evals"
EVALS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/files/evals", StaticFiles(directory=EVALS_DIR), name="pages")

DIST = PROJECT_DIR / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
