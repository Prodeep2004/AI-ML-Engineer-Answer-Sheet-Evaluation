import { useState } from 'react'
import type { Answer } from '../api'
import { ConfidencePill, ScoreMark, VerdictGlyph, fmt } from './Marks'

export default function QuestionCard({ a, onShowPage }: { a: Answer; onShowPage: (page: number) => void }) {
  const [open, setOpen] = useState(false)
  const written = a.raw_lines.filter(l => l.text.trim())

  return (
    <article className={`qcard c-${a.confidence}`}>
      <header className="q-head" onClick={() => a.pages[0] && onShowPage(a.pages[0])}>
        <div className="q-title">
          <span className="qno">{a.question_no}</span>
          <p className="q-text">{a.question}</p>
        </div>
        <ScoreMark score={a.score} max={a.max_marks} />
      </header>

      <div className="transcript">
        {written.length === 0 && <span className="muted">— no answer written —</span>}
        {written.map((l, i) => {
          const prevPage = i > 0 ? written[i - 1].page : l.page
          return (
            <div key={i}>
              {l.page !== prevPage && <div className="page-break">page {l.page}</div>}
              {l.is_diagram
                ? <span className="diagram">◇ {l.text.replace(/^\[DIAGRAM:\s*|\]$/g, '')}</span>
                : <span className={[
                    'ln', l.crossed_out && 'struck', l.margin_note && 'margin', l.legibility !== 'high' && `leg-${l.legibility}`,
                  ].filter(Boolean).join(' ')}>{l.text}</span>}
            </div>
          )
        })}
      </div>

      <ul className="criteria">
        {a.criteria.map(c => (
          <li key={c.id}>
            <VerdictGlyph v={c.verdict} />
            <div className="c-body">
              <span>{c.desc}</span>
              {c.evidence && <q>{c.evidence}</q>}
            </div>
            <span className="c-marks">{fmt(c.awarded)}/{fmt(c.marks)}</span>
          </li>
        ))}
      </ul>

      <footer className="q-foot">
        <ConfidencePill level={a.confidence} />
        <span className="reason">{a.reason}</span>
        <button className="link" onClick={() => setOpen(o => !o)} aria-expanded={open}>{open ? 'Hide' : 'Why?'}</button>
      </footer>

      {open && (
        <dl className="details">
          <div><dt>OCR agreement</dt><dd>{a.ocr_agreement != null ? `${a.ocr_agreement}%` : '—'}</dd></div>
          <div><dt>Semantic similarity</dt><dd>{a.embedding_similarity ?? '—'}{a.embedding_score != null && <> (≈ {a.embedding_score}/{a.max_marks})</>}</dd></div>
          <div><dt>Grading runs</dt><dd>{a.judge_run_scores.map(fmt).join(' · ')}</dd></div>
          <div>
            <dt>Pages</dt>
            <dd>{a.pages.length ? a.pages.map(p => <button key={p} className="link" onClick={() => onShowPage(p)}>p{p}</button>) : '—'}</dd>
          </div>
          {a.comment && <div className="wide"><dt>Examiner note</dt><dd>{a.comment}</dd></div>}
          {a.signals.length > 0 && (
            <div className="wide"><dt>All signals</dt><dd><ul>{a.signals.map(s => <li key={s}>{s}</li>)}</ul></dd></div>
          )}
        </dl>
      )}
    </article>
  )
}
