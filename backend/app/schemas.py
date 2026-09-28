"""Data contracts. The LLM-facing models double as Gemini JSON response schemas."""
from typing import Literal

from pydantic import BaseModel, Field

# ---------- Rubric ----------

class Criterion(BaseModel):
    id: str
    desc: str
    marks: float
    needs_diagram: bool = False


class RubricQuestion(BaseModel):
    qno: str
    question: str
    max_marks: float
    model_answer: str
    criteria: list[Criterion]
    diagram_expected: bool = False


class Rubric(BaseModel):
    id: str
    subject: str
    total_marks: float
    questions: list[RubricQuestion]


# ---------- Extraction (LLM response schema) ----------

class OcrLine(BaseModel):
    text: str = Field(description="Exact transcription of this line. For a drawing: '[DIAGRAM: description]'.")
    question_label: str | None = Field(
        default=None, description="Normalised label like 'Q3' ONLY if this line starts a new answer, else null."
    )
    crossed_out: bool = Field(default=False, description="True if the writer struck this line through.")
    margin_note: bool = Field(default=False, description="True if written in the margin / as a side note.")
    is_diagram: bool = Field(default=False, description="True if this entry describes a drawing, not text.")
    legibility: Literal["high", "medium", "low"] = "high"


class PageExtraction(BaseModel):
    lines: list[OcrLine]


# ---------- Scoring (LLM response schema) ----------

class CriterionVerdict(BaseModel):
    id: str
    verdict: Literal["met", "partial", "not_met"]
    evidence: str = Field(description="Short quote from the student answer supporting the verdict, or '' if none.")


class JudgeResult(BaseModel):
    criteria: list[CriterionVerdict]
    comment: str = Field(description="One sentence on the answer's overall quality.")


# ---------- Pipeline output ----------

class CriterionResult(BaseModel):
    id: str
    desc: str
    marks: float
    awarded: float
    verdict: str
    evidence: str
    agreement: float  # share of judge runs that agreed with the final verdict


class AnswerResult(BaseModel):
    question_no: str
    question: str
    pages: list[int]
    extracted_text: str
    raw_lines: list[dict]
    score: float
    max_marks: float
    score_vs_key: str
    criteria: list[CriterionResult]
    judge_run_scores: list[float]
    embedding_similarity: float | None
    embedding_score: float | None
    ocr_agreement: float | None
    confidence: Literal["high", "medium", "low"]
    reason: str
    signals: list[str]
    comment: str = ""


class EvaluationResult(BaseModel):
    rubric_id: str
    subject: str
    pages: int
    total_score: float
    total_marks: float
    elapsed_s: float
    models_used: dict[str, str]
    answers: list[AnswerResult]
