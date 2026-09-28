"""SQLite via SQLModel: rubrics + evaluation history. Results are stored as JSON blobs — they are
always read whole, so normalising them into tables would add joins without adding value."""
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.config import PROJECT_DIR, get_settings
from app.schemas import Rubric


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RubricRow(SQLModel, table=True):
    __tablename__ = "rubrics"
    id: str = Field(primary_key=True)
    subject: str
    total_marks: float
    n_questions: int
    data: str  # Rubric JSON
    updated_at: datetime = Field(default_factory=_now)


class EvaluationRow(SQLModel, table=True):
    __tablename__ = "evaluations"
    id: str = Field(primary_key=True)
    rubric_id: str = Field(index=True)
    subject: str
    status: str = "queued"  # queued | running | done | error
    stage: str = "queued"  # extract | structure | score | confidence | done
    detail: str = ""
    filenames: str = "[]"
    page_count: int = 0
    total_score: float | None = None
    total_marks: float | None = None
    low_count: int | None = None
    elapsed_s: float | None = None
    result: str | None = None  # EvaluationResult JSON
    error: str | None = None
    created_at: datetime = Field(default_factory=_now, index=True)


engine = create_engine(
    f"sqlite:///{get_settings().storage_dir / 'app.db'}", connect_args={"check_same_thread": False}
)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    seed_rubrics(PROJECT_DIR / "data" / "rubrics")


def session() -> Session:
    return Session(engine)


def upsert_rubric(r: Rubric) -> RubricRow:
    with session() as s:
        row = s.get(RubricRow, r.id) or RubricRow(id=r.id, subject="", total_marks=0, n_questions=0, data="")
        row.subject, row.total_marks, row.n_questions = r.subject, r.total_marks, len(r.questions)
        row.data, row.updated_at = r.model_dump_json(), _now()
        s.add(row)
        s.commit()
        s.refresh(row)
        return row


def seed_rubrics(folder: Path) -> None:
    """Load rubric JSON files shipped in data/rubrics (only if not already in the DB)."""
    if not folder.exists():
        return
    with session() as s:
        existing = set(s.exec(select(RubricRow.id)).all())
    for f in folder.glob("*.json"):
        r = Rubric.model_validate(json.loads(f.read_text(encoding="utf-8")))
        if r.id not in existing:
            upsert_rubric(r)


def get_rubric(rubric_id: str) -> Rubric | None:
    with session() as s:
        row = s.get(RubricRow, rubric_id)
        return Rubric.model_validate_json(row.data) if row else None


def update_eval(eval_id: str, **fields) -> None:
    with session() as s:
        row = s.get(EvaluationRow, eval_id)
        if row:
            for k, v in fields.items():
                setattr(row, k, v)
            s.add(row)
            s.commit()
