"""Run the full pipeline from the terminal.

    python cli.py ../data/samples --rubric ../data/rubrics/python_rubric.json
    python cli.py page1.jpg page2.jpg --rubric rubric.json --out ../outputs
"""
import argparse
import asyncio
import logging
import sys
from pathlib import Path

from app.config import PROJECT_DIR
from app.export import to_csv, to_json
from app.pipeline import preprocess
from app.pipeline.runner import evaluate
from app.schemas import Rubric

sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluate handwritten answer sheets")
    ap.add_argument("inputs", nargs="+", type=Path, help="images / PDFs / folders, in page order")
    ap.add_argument("--rubric", type=Path, default=PROJECT_DIR / "data/rubrics/python_rubric.json")
    ap.add_argument("--out", type=Path, default=PROJECT_DIR / "outputs")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="  %(message)s")

    rubric = Rubric.model_validate_json(args.rubric.read_text(encoding="utf-8"))
    files = preprocess.files_from_paths(args.inputs)
    if not files:
        sys.exit("No input images/PDFs found.")
    print(f"Evaluating {len(files)} file(s) against '{rubric.subject}'")

    result = asyncio.run(evaluate(files, rubric, on_progress=lambda s, d: print(f"  [{s}] {d}") if d else None))

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "results.json").write_text(to_json(result), encoding="utf-8")
    (args.out / "results.csv").write_text(to_csv(result), encoding="utf-8-sig")  # BOM so Excel shows ✓ ½ ✗

    print(f"\n{'Q':<4} {'Score':<24} {'Conf':<7} Reason")
    for a in result.answers:
        print(f"{a.question_no:<4} {a.score_vs_key:<24} {a.confidence:<7} {a.reason}")
    print(f"\nTotal {result.total_score:g}/{result.total_marks:g} · {result.elapsed_s}s · {result.models_used}")
    print(f"Wrote {args.out / 'results.json'} and results.csv")


if __name__ == "__main__":
    main()
