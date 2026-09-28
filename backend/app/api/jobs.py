"""Background evaluation job: preprocess, save page images for the UI, run the pipeline, persist."""
import asyncio
import logging
import shutil

from app import db
from app.config import get_settings
from app.pipeline import preprocess
from app.pipeline.runner import evaluate
from app.schemas import Rubric

log = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()  # keep references so tasks are not garbage-collected


def pages_dir(eval_id: str):
    return get_settings().storage_dir / "evals" / eval_id


async def _run(eval_id: str, files: list[tuple[str, bytes]], rubric: Rubric) -> None:
    try:
        db.update_eval(eval_id, status="running", stage="extract", detail="Cleaning pages")
        pages = await asyncio.to_thread(preprocess.prepare, files)
        out = pages_dir(eval_id)
        out.mkdir(parents=True, exist_ok=True)
        for p in pages:
            (out / f"page{p.page_no}.jpg").write_bytes(p.jpeg)
        db.update_eval(eval_id, page_count=len(pages))

        result = await evaluate(
            files, rubric, pages=pages,
            on_progress=lambda stage, detail: db.update_eval(eval_id, stage=stage, detail=detail),
        )
        db.update_eval(
            eval_id, status="done", stage="done", detail="",
            total_score=result.total_score, total_marks=result.total_marks, elapsed_s=result.elapsed_s,
            low_count=sum(a.confidence == "low" for a in result.answers), result=result.model_dump_json(),
        )
    except Exception as e:  # surface every failure to the UI instead of a silent hang
        log.exception("evaluation %s failed", eval_id)
        db.update_eval(eval_id, status="error", error=f"{type(e).__name__}: {e}"[:1000])


def start(eval_id: str, files: list[tuple[str, bytes]], rubric: Rubric) -> None:
    task = asyncio.create_task(_run(eval_id, files, rubric))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def delete_files(eval_id: str) -> None:
    shutil.rmtree(pages_dir(eval_id), ignore_errors=True)
