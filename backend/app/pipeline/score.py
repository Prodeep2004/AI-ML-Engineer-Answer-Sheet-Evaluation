"""Step 3 — Score: rubric-criterion LLM judge (self-consistency over N runs) + embedding similarity sanity check.

- All answers of a sheet are graded in ONE request per run (N requests total, not N × questions):
  far faster and stays inside free-tier rate limits.
- Marks are computed deterministically from verdicts (met = full, partial = half, not_met = 0),
  never taken from the model, so the same verdicts always give the same score.
- Final verdict per criterion = median over runs; disagreement between runs feeds confidence.
"""
import asyncio
import statistics

from pydantic import BaseModel

from app import cache
from app.config import get_settings
from app.llm.gemini import Gemini, cosine
from app.schemas import CriterionResult, CriterionVerdict, Rubric, RubricQuestion

PROMPT_VERSION = "judge-v3"
VERDICT_WEIGHT = {"met": 1.0, "partial": 0.5, "not_met": 0.0}


class QuestionJudgement(BaseModel):
    qno: str
    criteria: list[CriterionVerdict]
    comment: str


class SheetJudgement(BaseModel):
    answers: list[QuestionJudgement]


JUDGE_PROMPT = """You are a fair, consistent exam evaluator for {subject}.
Grade EACH student answer below against EACH of its rubric criteria independently, by MEANING — not keyword overlap.
- "met": the idea is clearly present and correct, in any wording.
- "partial": present but incomplete, vague, or partly wrong.
- "not_met": missing or wrong.
Answers were read from handwriting by OCR: ignore spelling mistakes and small OCR glitches
(e.g. "mutabel" = mutable, "yeild" = yield), but never invent content that is not written.
[DIAGRAM: ...] is a text description of a hand-drawn diagram — judge the diagram from it.
[MARGIN NOTE: ...] is part of the answer. Grade each question only on its own answer.

{blocks}

Return one entry per question (qno as given) with a verdict for every criterion id, a short quote from
the student's answer as evidence ('' if none), and a one-sentence comment."""

BLOCK = """=== {qno} ({max_marks} marks) ===
QUESTION: {question}
MODEL ANSWER (reference only; wording need not match): {model_answer}
CRITERIA:
{criteria}
STUDENT ANSWER:
<<<
{answer}
>>>"""


def _block(q: RubricQuestion, answer: str) -> str:
    crit = "\n".join(f"- {c.id} ({c.marks:g} marks): {c.desc}" for c in q.criteria)
    return BLOCK.format(qno=q.qno, max_marks=f"{q.max_marks:g}", question=q.question,
                        model_answer=q.model_answer, criteria=crit, answer=answer)


async def _judge_run(llm: Gemini, prompt: str, run: int) -> SheetJudgement:
    k = cache.key(PROMPT_VERSION, prompt, str(run))
    if (hit := cache.get(k)) is not None:
        return SheetJudgement.model_validate(hit)
    temp = 0.0 if run == 0 else 0.5  # run 0 deterministic; others sample so disagreement can surface
    res, _ = await llm.generate_json(get_settings().primary_chain, [prompt], SheetJudgement, temperature=temp)
    cache.put(k, res.model_dump())
    return res


def _round_half(x: float) -> float:
    return round(x * 2) / 2


def _aggregate(q: RubricQuestion, runs: list[dict[str, CriterionVerdict]], comment: str) -> dict:
    crit_results, run_scores = [], [0.0] * len(runs)
    for c in q.criteria:
        verdicts = [r[c.id].verdict if c.id in r else "not_met" for r in runs]
        awards = [VERDICT_WEIGHT[v] * c.marks for v in verdicts]
        for i, a in enumerate(awards):
            run_scores[i] += a
        final = statistics.median(awards)
        final_verdict = min(VERDICT_WEIGHT, key=lambda v: abs(VERDICT_WEIGHT[v] * c.marks - final))
        evidence = next((r[c.id].evidence for r in runs if c.id in r and r[c.id].verdict == final_verdict), "")
        crit_results.append(CriterionResult(
            id=c.id, desc=c.desc, marks=c.marks, awarded=final, verdict=final_verdict, evidence=evidence,
            agreement=sum(v == final_verdict for v in verdicts) / len(verdicts),
        ))
    return {"criteria": crit_results, "score": _round_half(sum(c.awarded for c in crit_results)),
            "run_scores": run_scores, "comment": comment}


def _blank(q: RubricQuestion) -> dict:
    crit = [CriterionResult(id=c.id, desc=c.desc, marks=c.marks, awarded=0, verdict="not_met",
                            evidence="", agreement=1.0) for c in q.criteria]
    return {"criteria": crit, "score": 0.0, "run_scores": [0.0], "comment": "No answer written."}


async def judge_all(llm: Gemini, rubric: Rubric, texts: dict[str, str]) -> dict[str, dict]:
    """Grade every non-blank answer; returns qno -> {criteria, score, run_scores, comment}."""
    todo = [q for q in rubric.questions if texts.get(q.qno, "").strip()]
    out = {q.qno: _blank(q) for q in rubric.questions if q not in todo}
    if not todo:
        return out

    prompt = JUDGE_PROMPT.format(subject=rubric.subject, blocks="\n\n".join(_block(q, texts[q.qno]) for q in todo))
    n = max(1, get_settings().judge_runs)
    results = await asyncio.gather(*[_judge_run(llm, prompt, i) for i in range(n)], return_exceptions=True)
    runs = [r for r in results if isinstance(r, SheetJudgement)]
    if not runs:
        raise RuntimeError(f"Grading failed: {results[0]}")

    for q in todo:
        per_run, comment = [], ""
        for r in runs:
            qj = next((a for a in r.answers if a.qno.strip().upper() == q.qno.upper()), None)
            if qj:
                per_run.append({v.id: v for v in qj.criteria})
                comment = comment or qj.comment
        out[q.qno] = _aggregate(q, per_run, comment) if per_run else _blank(q) | {"comment": "Grader returned nothing."}
        out[q.qno]["runs_ok"] = f"{len(per_run)}/{n}"
    return out


# Calibrated on real answers: on-topic-but-thin answers land ~0.74–0.84, so similarity measures topicality
# more than completeness. Map [0.70 … 0.95] onto marks; it is a sanity check, never the score.
SIM_FLOOR, SIM_CEIL = 0.70, 0.95


async def embedding_scores(llm: Gemini, pairs: list[tuple[str, str, float]]) -> list[tuple[float | None, float | None]]:
    """pairs: (student_answer, model_answer, max_marks) -> (cosine, marks-equivalent). One batched call."""
    idx = [i for i, (a, _, _) in enumerate(pairs) if a.strip()]
    out: list[tuple[float | None, float | None]] = [(None, None)] * len(pairs)
    if not idx:
        return out
    texts = [pairs[i][0] for i in idx] + [pairs[i][1] for i in idx]
    k = cache.key("emb-v1", get_settings().embed_model, *texts)
    vecs = cache.get(k)
    if vecs is None:
        try:
            vecs = await llm.embed(texts)
            cache.put(k, vecs)
        except Exception:
            return out
    for j, i in enumerate(idx):
        sim = cosine(vecs[j], vecs[len(idx) + j])
        frac = min(1.0, max(0.0, (sim - SIM_FLOOR) / (SIM_CEIL - SIM_FLOOR)))
        out[i] = (round(sim, 3), round(frac * pairs[i][2], 2))
    return out
