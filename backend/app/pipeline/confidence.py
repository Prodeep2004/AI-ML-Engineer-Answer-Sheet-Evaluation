"""Step 4 — Confidence: explainable rules over independent signals.

Each signal is MAJOR (a human should re-check) or MINOR (worth knowing).
  any MAJOR -> low · any MINOR -> medium · none -> high
The reason line is the most severe signal(s). Thresholds are hand-set; with graded data
they should be calibrated against actual human-vs-model disagreement.
"""
import re

from rapidfuzz import fuzz

from app.pipeline.segment import Segment
from app.schemas import CriterionResult, RubricQuestion

MAJOR, MINOR = 2, 1


def ocr_agreement(primary: Segment | None, cross: Segment | None) -> float:
    """0–100 similarity between the two independent readers' text for this answer."""
    norm = lambda s: re.sub(r"\s+", " ", s.lower()).strip()
    a = norm(primary.scoring_text) if primary else ""
    b = norm(cross.scoring_text) if cross else ""
    if not a and not b:
        return 100.0
    return round(fuzz.ratio(a, b), 1)


def assess(
    q: RubricQuestion,
    seg: Segment | None,
    cross_available: bool,
    agreement: float | None,
    criteria: list[CriterionResult],
    score: float,
    run_scores: list[float],
    emb_score: float | None,
    runs_ok: str | None = None,
) -> tuple[str, str, list[str]]:
    signals: list[tuple[int, str]] = []
    text = seg.scoring_text if seg else ""

    # --- blank / missing answers: confident zero only when both readers agree it's empty
    if not text.strip():
        if cross_available and agreement is not None and agreement < 100:
            return "low", "Primary reader saw no answer but the cross-check reader found text — verify.", ["blank-disagreement"]
        why = "Question number written but no answer given." if seg else "No answer found for this question."
        return "high", why + " Awarded 0.", ["blank"]

    st = seg.stats

    # --- extraction signals
    if agreement is not None:
        if agreement < 65:
            signals.append((MAJOR, f"The two OCR readers disagree heavily ({agreement:.0f}% match) — handwriting may be misread"))
        elif agreement < 82:
            signals.append((MINOR, f"OCR readers partly disagree ({agreement:.0f}% match)"))
    if st["low_legibility_share"] >= 0.3 or st["unreadable_marks"] >= 3:
        signals.append((MAJOR, "Large parts of the handwriting are barely legible"))
    elif st["low_legibility_share"] > 0 or st["medium_legibility_share"] >= 0.4 or st["unreadable_marks"]:
        signals.append((MINOR, "Some words were hard to read"))
    if st["crossed_out"]:
        signals.append((MINOR, f"{st['crossed_out']} crossed-out line(s) excluded from grading"))

    # --- structure signals
    if len(seg.pages) > 1:
        sev = MINOR
        signals.append((sev, f"Answer spans pages {', '.join(map(str, seg.pages))} and was stitched together"))
    if "model" not in seg.label_sources:
        signals.append((MINOR, "Question number found only by pattern-matching"))

    # --- scoring signals
    max_m = q.max_marks
    spread = max(run_scores) - min(run_scores) if run_scores else 0
    if spread >= max(1.0, 0.2 * max_m):
        signals.append((MAJOR, f"Repeated grading runs disagree by {spread:g} marks"))
    elif spread > 0:
        signals.append((MINOR, f"Grading runs varied by {spread:g} marks"))
    if runs_ok and runs_ok.split("/")[0] == "1" and runs_ok != "1/1":
        signals.append((MINOR, f"Only {runs_ok} grading runs succeeded — consistency unverified"))
    shaky = [c.id for c in criteria if c.agreement < 1.0]
    if len(shaky) >= 2:
        signals.append((MINOR, f"Unstable verdicts on {', '.join(shaky)}"))

    if emb_score is not None:
        gap = abs(emb_score - score) / max_m
        if gap >= 0.45:
            signals.append((MAJOR, f"Rubric score ({score:g}) and semantic similarity ({emb_score:.1f}) strongly disagree"))
        elif gap >= 0.3:
            signals.append((MINOR, "Rubric score and semantic similarity differ noticeably"))

    diag_crit = [c for c in criteria if any(k.id == c.id and k.needs_diagram for k in q.criteria)]
    if diag_crit and st["diagrams"] and any(c.awarded > 0 for c in diag_crit):
        signals.append((MINOR, "Diagram marks were given from a text description of the drawing"))
    elif q.diagram_expected and not st["diagrams"] and "diagram" in text.lower():
        signals.append((MAJOR, "Answer mentions a diagram the reader could not detect"))

    partial = sum(c.verdict == "partial" for c in criteria)
    if partial and partial >= len(criteria) / 2:
        signals.append((MINOR, "Mostly partial credit — graded on judgement calls"))
    if st["words"] < 6 and score > 0:
        signals.append((MINOR, "Very short answer"))
    if st["margin_notes"]:
        signals.append((MINOR, "Includes margin notes"))

    if not signals:
        return "high", "Clear handwriting, readers agree and grading runs are consistent.", []
    signals.sort(key=lambda s: -s[0])
    level = "low" if signals[0][0] == MAJOR else "medium"
    top = [m for sev, m in signals if sev == signals[0][0]][:2]
    return level, "; ".join(top) + ".", [m for _, m in signals]
