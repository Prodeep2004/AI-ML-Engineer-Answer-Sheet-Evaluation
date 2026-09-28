import json
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from sqlmodel import col, select

from app import db, export
from app.api import jobs
from app.pipeline.preprocess import IMAGE_EXT
from app.schemas import EvaluationResult, Rubric

router = APIRouter(prefix="/api")
MAX_FILES, MAX_BYTES = 30, 25 * 1024 * 1024


@router.get("/health")
def health():
    return {"ok": True}


# ---------- rubrics ----------

@router.get("/rubrics")
def list_rubrics():
    with db.session() as s:
        rows = s.exec(select(db.RubricRow).order_by(col(db.RubricRow.updated_at).desc())).all()
    return [{"id": r.id, "subject": r.subject, "total_marks": r.total_marks, "n_questions": r.n_questions}
            for r in rows]


@router.get("/rubrics/{rubric_id}", response_model=Rubric)
def get_rubric(rubric_id: str):
    r = db.get_rubric(rubric_id)
    if not r:
        raise HTTPException(404, "Rubric not found")
    return r


@router.put("/rubrics/{rubric_id}")
def save_rubric(rubric_id: str, rubric: Rubric):
    if rubric.id != rubric_id:
        raise HTTPException(400, "Rubric id mismatch")
    ids = [q.qno for q in rubric.questions]
    if len(ids) != len(set(ids)):
        raise HTTPException(400, "Duplicate question numbers")
    rubric.total_marks = sum(q.max_marks for q in rubric.questions)
    db.upsert_rubric(rubric)
    return rubric


@router.delete("/rubrics/{rubric_id}")
def delete_rubric(rubric_id: str):
    with db.session() as s:
        row = s.get(db.RubricRow, rubric_id)
        if not row:
            raise HTTPException(404, "Rubric not found")
        s.delete(row)
        s.commit()
    return {"ok": True}


# ---------- evaluations ----------

@router.post("/evaluations")
async def create_evaluation(rubric_id: str = Form(...), files: list[UploadFile] = File(...)):
    rubric = db.get_rubric(rubric_id)
    if not rubric:
        raise HTTPException(404, "Rubric not found")
    if not files or len(files) > MAX_FILES:
        raise HTTPException(400, f"Upload 1–{MAX_FILES} files")
    payload = []
    for f in files:
        name = f.filename or "page.jpg"
        ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if ext not in IMAGE_EXT | {".pdf"}:
            raise HTTPException(400, f"Unsupported file type: {name}")
        data = await f.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(400, f"{name} is larger than 25 MB")
        payload.append((name, data))

    eval_id = uuid.uuid4().hex[:12]
    with db.session() as s:
        s.add(db.EvaluationRow(id=eval_id, rubric_id=rubric.id, subject=rubric.subject,
                               filenames=json.dumps([n for n, _ in payload])))
        s.commit()
    jobs.start(eval_id, payload, rubric)
    return {"id": eval_id}


def _summary(r: db.EvaluationRow) -> dict:
    return {
        "id": r.id, "rubric_id": r.rubric_id, "subject": r.subject, "status": r.status, "stage": r.stage,
        "detail": r.detail, "filenames": json.loads(r.filenames), "page_count": r.page_count,
        "total_score": r.total_score, "total_marks": r.total_marks, "low_count": r.low_count,
        "elapsed_s": r.elapsed_s, "error": r.error, "created_at": r.created_at.replace(tzinfo=None).isoformat() + "Z",
    }


@router.get("/evaluations")
def list_evaluations(limit: int = 50):
    with db.session() as s:
        rows = s.exec(select(db.EvaluationRow).order_by(col(db.EvaluationRow.created_at).desc()).limit(limit)).all()
    return [_summary(r) for r in rows]


@router.get("/evaluations/{eval_id}")
def get_evaluation(eval_id: str):
    with db.session() as s:
        row = s.get(db.EvaluationRow, eval_id)
    if not row:
        raise HTTPException(404, "Evaluation not found")
    out = _summary(row)
    out["pages"] = [f"/files/evals/{eval_id}/page{i}.jpg" for i in range(1, row.page_count + 1)]
    out["result"] = json.loads(row.result) if row.result else None
    return out


@router.get("/evaluations/{eval_id}/export")
def export_evaluation(eval_id: str, fmt: str = "json"):
    with db.session() as s:
        row = s.get(db.EvaluationRow, eval_id)
    if not row or not row.result:
        raise HTTPException(404, "No finished result")
    result = EvaluationResult.model_validate_json(row.result)
    if fmt == "csv":
        body, media = "﻿" + export.to_csv(result), "text/csv; charset=utf-8"
    else:
        body, media, fmt = export.to_json(result), "application/json", "json"
    return Response(body, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="results-{eval_id}.{fmt}"'})


@router.delete("/evaluations/{eval_id}")
def delete_evaluation(eval_id: str):
    with db.session() as s:
        row = s.get(db.EvaluationRow, eval_id)
        if not row:
            raise HTTPException(404, "Evaluation not found")
        s.delete(row)
        s.commit()
    jobs.delete_files(eval_id)
    return {"ok": True}
