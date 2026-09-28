"""Step 2 — Structure: a state machine that walks every line of every page and assigns it to a question.

- A labelled line opens (or re-opens, e.g. "Q3 contd.") that question.
- An unlabelled line continues the currently open question — this is how an answer that spills onto
  the next page, or resumes after a diagram, stays in one piece.
- Labels come from the vision model; a regex fallback catches labels the model missed.
"""
import re
from dataclasses import dataclass, field

from app.schemas import PageExtraction

LABEL_RE = re.compile(r"^\s*(?:Q(?:ue(?:stion)?)?\.?\s*|Ans(?:wer)?\.?\s*)?\(?(\d{1,2})\s*[\).:\-]", re.I)
STRIP_RE = re.compile(r"^\s*(?:Q(?:ue(?:stion)?)?\.?\s*|Ans(?:wer)?\.?\s*)?\(?\d{1,2}\s*[\).:\-]\s*", re.I)


@dataclass
class Segment:
    qno: str
    lines: list[dict] = field(default_factory=list)
    pages: list[int] = field(default_factory=list)
    label_sources: set[str] = field(default_factory=set)
    continued_unlabelled: bool = False  # picked up lines on a later page with no label

    @property
    def scoring_text(self) -> str:
        """Text the judge sees: crossed-out lines removed, diagrams and margin notes tagged in place."""
        out = []
        for ln in self.lines:
            if ln["crossed_out"]:
                continue
            t = ln["text"].rstrip()  # keep leading spaces: code indentation matters when grading Python
            if not t.strip():
                continue
            out.append(f"[MARGIN NOTE: {t}]" if ln["margin_note"] and not ln["is_diagram"] else t)
        return "\n".join(out)

    @property
    def stats(self) -> dict:
        written = [l for l in self.lines if l["text"].strip()]
        n = max(len(written), 1)
        return {
            "n_lines": len(written),
            "crossed_out": sum(l["crossed_out"] for l in written),
            "diagrams": sum(l["is_diagram"] for l in written),
            "margin_notes": sum(l["margin_note"] for l in written),
            "low_legibility_share": sum(l["legibility"] == "low" for l in written) / n,
            "medium_legibility_share": sum(l["legibility"] == "medium" for l in written) / n,
            "unreadable_marks": sum(l["text"].count("[?") for l in written),
            "words": len(self.scoring_text.split()),
        }


def _norm(label: str | None) -> str | None:
    if not label:
        return None
    m = re.search(r"\d{1,2}", label)
    return f"Q{int(m.group())}" if m else None


def segment(pages: list[PageExtraction], valid_qnos: list[str]) -> dict[str, Segment]:
    valid = set(valid_qnos)
    segs: dict[str, Segment] = {}
    current: Segment | None = None

    for page_no, page in enumerate(pages, start=1):
        first_on_page = True
        for raw in page.lines:
            ln = raw.model_dump()
            model_label = _norm(ln["question_label"])
            m = LABEL_RE.match(ln["text"]) if not ln["is_diagram"] else None
            regex_label = f"Q{int(m.group(1))}" if m else None
            label = model_label or regex_label
            if label not in valid:
                label = None  # e.g. a "1." inside a numbered list within an answer

            if label:
                current = segs.setdefault(label, Segment(label))
                current.label_sources.add("model" if model_label == label else "regex")
                if regex_label == label:
                    current.label_sources.add("regex")
                ln["text"] = STRIP_RE.sub("", ln["text"], count=1)
            elif current is None:
                continue  # preamble before the first answer (name, roll no.)
            elif first_on_page and page_no not in current.pages:
                current.continued_unlabelled = True

            ln["page"] = page_no
            current.lines.append(ln)
            if page_no not in current.pages:
                current.pages.append(page_no)
            first_on_page = False
    return segs
