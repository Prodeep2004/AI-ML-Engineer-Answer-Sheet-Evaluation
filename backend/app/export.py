"""Deliverable writers: JSON (full detail) and CSV (one row per question, the fields the brief asks for)."""
import csv
import io
import json

from app.schemas import EvaluationResult

CSV_FIELDS = [
    "question_no", "extracted_answer_text", "score", "max_marks", "score_vs_key",
    "confidence", "reason", "pages", "ocr_agreement", "embedding_similarity", "judge_run_scores",
]


def to_json(r: EvaluationResult) -> str:
    return json.dumps(r.model_dump(), indent=2, ensure_ascii=False)


def to_csv(r: EvaluationResult) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
    w.writeheader()
    for a in r.answers:
        w.writerow({
            "question_no": a.question_no,
            "extracted_answer_text": a.extracted_text,
            "score": a.score,
            "max_marks": a.max_marks,
            "score_vs_key": a.score_vs_key,
            "confidence": a.confidence,
            "reason": a.reason,
            "pages": " ".join(map(str, a.pages)),
            "ocr_agreement": a.ocr_agreement,
            "embedding_similarity": a.embedding_similarity,
            "judge_run_scores": " ".join(f"{s:g}" for s in a.judge_run_scores),
        })
    return buf.getvalue()
