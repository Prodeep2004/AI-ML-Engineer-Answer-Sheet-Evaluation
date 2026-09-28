import { useEffect, useState } from 'react'
import { api, type RubricSummary } from '../api'

export default function Rubrics() {
  const [list, setList] = useState<RubricSummary[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => { api.rubrics().then(setList).catch(e => setError(e.message)) }, [])

  return (
    <div className="rubrics">
      <div className="eval-head">
        <div>
          <h1>Rubrics</h1>
          <p className="muted small">Answer keys the scorer grades against, one mark-bearing point at a time.</p>
        </div>
        <a className="btn primary" href="#/rubrics/new">New rubric</a>
      </div>
      {error && <p className="error">{error}</p>}
      <ul className="rubric-list">
        {list?.map(r => (
          <li key={r.id}>
            <a href={`#/rubrics/${encodeURIComponent(r.id)}`} className="history-row">
              <span className="h-subject">{r.subject}</span>
              <span className="muted small mono">{r.id}</span>
              <span className="muted small">{r.n_questions} questions · {r.total_marks} marks</span>
            </a>
          </li>
        ))}
        {list?.length === 0 && <li className="muted empty">No rubrics yet.</li>}
      </ul>
    </div>
  )
}
