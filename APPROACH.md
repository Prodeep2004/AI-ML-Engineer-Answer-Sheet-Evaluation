# Approach note

1. **Extract:** each page is read by two different Gemini vision models on their own (a primary reader and a cheaper cross-check reader). The primary returns structured lines with question labels, crossed-out / margin / diagram flags and a legibility score per line. How closely the two readers agree becomes a real OCR-confidence signal, instead of trusting the model's view of itself.
2. **Structure:** a line-by-line state machine across pages. A labelled line opens a question; an unlabelled line continues it, so answers that spill onto the next page or resume after a diagram stay in one piece. A regex catches labels the model missed.
3. **Score:** an LLM grades each rubric point as met, partial or not met, quoting the student's words as evidence. Marks are computed from those verdicts by code, never taken from the model's own marks, so the same verdicts always give the same score. There are 3 grading runs and the median is taken; how much they disagree is itself a signal. Embedding similarity is kept only as a sanity check, because on real answers it measured whether an answer was on topic, not whether it was complete.
4. **Confidence:** explainable rules, where any major signal gives low and any minor signal gives medium. The signals are: readers disagreeing, low legibility, grading runs disagreeing, rubric score far from similarity, diagram-dependent marks, answers stitched across pages, and crossed-out lines. A blank answer is a *confident* zero only when both readers agree it's empty.
5. **Tradeoffs:** I used a vision LLM rather than a trained handwriting model (no time to train one), and hand-set thresholds rather than a learned calibrator. All answers are graded in one request per run, which cut requests from 24 to 3 to fit free-tier rate limits.

**Weakest points:**
- The thresholds were tuned on a single script. Nothing is calibrated against human graders yet.
- Diagrams are graded from the model's *text description*, so wrong arrows can be described as right.
- Indentation in handwritten code is only as good as the reader's guess.
- Both readers are from the same model family, so their errors can overlap.

**With more time:**
- Collect human-graded scripts and fit the confidence thresholds so predicted confidence matches actual error rates.
- Add a non-LLM OCR engine (TrOCR or PaddleOCR) as a truly independent reader.
- Use layout detection to crop answer regions and grade diagrams from the image itself.
- Support Indic scripts.
- For scale: a queue with batch APIs, image-hash caching (already in place), a cheap model first and escalation only for low-confidence answers, and a human-review queue driven by the "Needs review" flag.
