"""Orchestrates Extract -> Structure -> Score -> Confidence. Everything that can run concurrently does."""
import asyncio
import time
from collections.abc import Awaitable, Callable

from app.llm.gemini import Gemini
from app.pipeline import confidence, extract, preprocess, score, segment
from app.schemas import AnswerResult, EvaluationResult, Rubric

Progress = Callable[[str, str], Awaitable[None] | None]
MARK = {"met": "✓", "partial": "½", "not_met": "✗"}


async def _emit(cb: Progress | None, stage: str, detail: str = "") -> None:
    if cb:
        r = cb(stage, detail)
        if asyncio.iscoroutine(r):
            await r


async def evaluate(
    files: list[tuple[str, bytes]],
    rubric: Rubric,
    on_progress: Progress | None = None,
    pages: list[preprocess.PageImage] | None = None,
) -> EvaluationResult:
    t0 = time.perf_counter()
    llm = Gemini()
    qnos = [q.qno for q in rubric.questions]

    await _emit(on_progress, "extract", "Cleaning pages")
    pages = pages or await asyncio.to_thread(preprocess.prepare, files)
    await _emit(on_progress, "extract", f"Reading {len(pages)} page(s) with two readers")
    prim_pages, cross_pages, models = await extract.extract_pages(llm, pages, rubric.subject, qnos)

    await _emit(on_progress, "structure", "Segmenting answers by question")
    segs = segment.segment(prim_pages, qnos)
    cross_ok = all(p is not None for p in cross_pages)
    cross_segs = segment.segment(cross_pages, qnos) if cross_ok else {}

    await _emit(on_progress, "score", f"Grading {len(qnos)} answers")
    texts = {q.qno: segs[q.qno].scoring_text if q.qno in segs else "" for q in rubric.questions}
    judged, embs = await asyncio.gather(
        score.judge_all(llm, rubric, texts),
        score.embedding_scores(llm, [(texts[q.qno], q.model_answer, q.max_marks) for q in rubric.questions]),
    )

    await _emit(on_progress, "confidence", "Flagging uncertain answers")
    answers: list[AnswerResult] = []
    for q, (sim, emb_score) in zip(rubric.questions, embs):
        j = judged[q.qno]
        seg = segs.get(q.qno)
        agree = confidence.ocr_agreement(seg, cross_segs.get(q.qno)) if cross_ok else None
        level, reason, signals = confidence.assess(
            q, seg, cross_ok, agree, j["criteria"], j["score"], j["run_scores"], emb_score, j.get("runs_ok")
        )
        answers.append(AnswerResult(
            question_no=q.qno,
            question=q.question,
            pages=seg.pages if seg else [],
            extracted_text=texts[q.qno],
            raw_lines=seg.lines if seg else [],
            score=j["score"],
            max_marks=q.max_marks,
            score_vs_key=f"{j['score']:g}/{q.max_marks:g} · "
                         + " ".join(f"{c.id}{MARK[c.verdict]}" for c in j["criteria"]),
            criteria=j["criteria"],
            judge_run_scores=j["run_scores"],
            embedding_similarity=sim,
            embedding_score=emb_score,
            ocr_agreement=agree,
            confidence=level,
            reason=reason,
            signals=signals,
            comment=j["comment"],
        ))

    await _emit(on_progress, "done", "")
    return EvaluationResult(
        rubric_id=rubric.id,
        subject=rubric.subject,
        pages=len(pages),
        total_score=sum(a.score for a in answers),
        total_marks=rubric.total_marks,
        elapsed_s=round(time.perf_counter() - t0, 1),
        models_used=models,
        answers=answers,
    )
