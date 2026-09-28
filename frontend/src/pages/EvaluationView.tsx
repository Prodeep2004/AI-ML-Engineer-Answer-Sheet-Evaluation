import { useEffect, useMemo, useState } from 'react'
import { api, type Confidence, type Evaluation } from '../api'
import { ScoreMark } from '../components/Marks'
import QuestionCard from '../components/QuestionCard'
import Stepper from '../components/Stepper'

type Filter = 'all' | Confidence

export default function EvaluationView({ id }: { id: string }) {
  const [ev, setEv] = useState<Evaluation | null>(null)
  const [error, setError] = useState('')
  const [page, setPage] = useState(0)
  const [filter, setFilter] = useState<Filter>('all')

  useEffect(() => {
    let alive = true
    let timer: number
    const tick = async () => {
      try {
        const e = await api.evaluation(id)
        if (!alive) return
        setEv(e)
        if (e.status === 'queued' || e.status === 'running') timer = window.setTimeout(tick, 1000)
      } catch (e) {
        if (alive) setError((e as Error).message)
      }
    }
    tick()
    return () => { alive = false; clearTimeout(timer) }
  }, [id])

  const result = ev?.result
  const counts = useMemo(() => {
    const c = { high: 0, medium: 0, low: 0 }
    result?.answers.forEach(a => c[a.confidence]++)
    return c
  }, [result])

  if (error) return <div className="panel"><p className="error">{error}</p><a href="#/">← Back</a></div>
  if (!ev) return <div className="loading">Loading…</div>

  const pages = ev.pages ?? []
  const answers = (result?.answers ?? []).filter(a => filter === 'all' || a.confidence === filter)

  return (
    <div className="eval">
      <div className="eval-head">
        <div>
          <a href="#/" className="back">← All scripts</a>
          <h1>{ev.subject}</h1>
          <p className="muted small">
            {ev.filenames.join(', ')}
            {result && <> · {result.pages} page{result.pages > 1 ? 's' : ''} · {result.elapsed_s}s</>}
          </p>
        </div>
        {result && <ScoreMark score={result.total_score} max={result.total_marks} />}
      </div>

      {(ev.status === 'queued' || ev.status === 'running') && (
        <section className="panel">
          <Stepper stage={ev.stage} detail={ev.detail} />
        </section>
      )}

      {ev.status === 'error' && (
        <section className="panel">
          <p className="error"><b>Evaluation failed.</b> {ev.error}</p>
          <p className="muted small">If Gemini was overloaded, go back and run it again. Pages already read are cached.</p>
        </section>
      )}

      {result && (
        <div className="toolbar">
          <div className="tabs" role="tablist">
            {(['all', 'low', 'medium', 'high'] as Filter[]).map(f => (
              <button key={f} role="tab" aria-selected={filter === f} className={filter === f ? 'on' : ''} onClick={() => setFilter(f)}>
                {f === 'all' ? `All ${result.answers.length}` : f === 'low' ? `Needs review ${counts.low}` : `${f[0].toUpperCase() + f.slice(1)} ${counts[f]}`}
              </button>
            ))}
          </div>
          <div className="exports">
            <a className="btn ghost" href={api.exportUrl(id, 'csv')}>CSV</a>
            <a className="btn ghost" href={api.exportUrl(id, 'json')}>JSON</a>
          </div>
        </div>
      )}

      <div className={`eval-body ${pages.length ? '' : 'no-pages'}`}>
        {pages.length > 0 && (
          <aside className="viewer">
            <div className="sheet"><img src={pages[page]} alt={`Page ${page + 1}`} /></div>
            {pages.length > 1 && (
              <div className="pager">
                {pages.map((_, i) => (
                  <button key={i} className={i === page ? 'on' : ''} onClick={() => setPage(i)}>{i + 1}</button>
                ))}
              </div>
            )}
          </aside>
        )}

        {result && (
          <div className="answers">
            {answers.map(a => (
              <QuestionCard key={a.question_no} a={a} onShowPage={p => setPage(Math.min(p - 1, pages.length - 1))} />
            ))}
            {answers.length === 0 && <p className="muted empty">Nothing in this group.</p>}
          </div>
        )}
      </div>
    </div>
  )
}
