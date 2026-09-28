"""Step 1 — Extract: two independent vision readers per page (primary + cross-check), cached by image hash."""
import asyncio

from google.genai import types

from app import cache
from app.config import get_settings
from app.llm.gemini import Gemini
from app.pipeline.preprocess import PageImage
from app.schemas import PageExtraction

PROMPT_VERSION = "extract-v2"

PRIMARY_PROMPT = """You are an expert examiner transcribing a HANDWRITTEN exam answer sheet ({subject}).
Expected question numbers: {qnos}.

Transcribe EXACTLY what is written, top to bottom, one entry per written line.
Rules:
- Do NOT correct spelling, grammar or code. Keep the student's mistakes. Preserve code indentation with spaces.
- question_label: set ONLY on the line where a new answer begins (e.g. "Q1)", "Q.3", "Ans 2", "3)", "(4)").
  Normalise to "Q<number>". Every other line: null. If a page starts mid-answer with no label, leave it null.
- crossed_out: true for any line/word group the student struck through (still transcribe it).
- margin_note: true for text written in the margin or squeezed in as a side note / insertion.
- Drawings (boxes, arrows, memory diagrams, flowcharts): emit ONE entry with is_diagram=true and
  text "[DIAGRAM: <what it shows, including every label and arrow>]" at the position it appears.
- Unreadable word: write your best guess wrapped like [?guess?] and lower that line's legibility.
- legibility: high = certain, medium = some guessing, low = mostly guessing.
- A question number written with nothing after it is still a line: emit it with its label and text "".
"""

CROSSCHECK_PROMPT = """Transcribe this handwritten exam page line by line, exactly as written (no corrections).
Set question_label ("Q1", "Q2", ...) only on lines where a new numbered answer starts.
Mark struck-through lines crossed_out=true. Describe drawings as "[DIAGRAM: ...]" with is_diagram=true.
Expected question numbers: {qnos}."""


async def _read(llm: Gemini, page: PageImage, chain: list[str], prompt: str, tag: str) -> tuple[PageExtraction, str]:
    k = cache.key(PROMPT_VERSION, tag, page.sha, prompt)
    if (hit := cache.get(k)) is not None:
        return PageExtraction.model_validate(hit["data"]), hit["model"] + " (cached)"
    parts = [types.Part.from_bytes(data=page.jpeg, mime_type="image/jpeg"), prompt]
    result, model = await llm.generate_json(chain, parts, PageExtraction, temperature=0.0)
    cache.put(k, {"data": result.model_dump(), "model": model})
    return result, model


async def extract_pages(
    llm: Gemini, pages: list[PageImage], subject: str, qnos: list[str]
) -> tuple[list[PageExtraction], list[PageExtraction | None], dict[str, str]]:
    """Run primary and cross-check readers on every page concurrently.
    The cross-check is best-effort: if it fails, confidence falls back to other signals."""
    s = get_settings()
    p1 = PRIMARY_PROMPT.format(subject=subject, qnos=", ".join(qnos))
    p2 = CROSSCHECK_PROMPT.format(qnos=", ".join(qnos))

    async def safe_cross(page):
        try:
            return await _read(llm, page, s.crosscheck_chain, p2, "cross")
        except Exception:
            return None, "unavailable"

    primary = [_read(llm, p, s.primary_chain, p1, "primary") for p in pages]
    cross = [safe_cross(p) for p in pages]
    res = await asyncio.gather(*primary, *cross)
    prim, crs = res[: len(pages)], res[len(pages):]
    models = {"reader": prim[0][1] if prim else "", "cross_reader": crs[0][1] if crs else ""}
    return [r for r, _ in prim], [r for r, _ in crs], models
