import { useEffect, useState } from 'react'
import { api, type Evaluation, type RubricSummary } from '../api'
import DropZone from '../components/DropZone'
import { ScoreMark } from '../components/Marks'

export default function Home() {
  const [rubrics, setRubrics] = useState<RubricSummary[]>([])
  const [rubricId, setRubricId] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [history, setHistory] = useState<Evaluation[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.rubrics().then(r => { setRubrics(r); setRubricId(id => id || r[0]?.id || '') }).catch(e => setError(e.message))
    api.evaluations().then(setHistory).catch(() => {})
  }, [])

  const submit = async () => {
    setBusy(true); setError('')
    try {
      const { id } = await api.evaluate(rubricId, files)
      location.hash = `#/e/${id}`
    } catch (e) {
      setError((e as Error).message); setBusy(false)
    }
  }

  const remove = async (id: string) => {
    await api.deleteEvaluation(id)
    setHistory(h => h.filter(e => e.id !== id))
  }

  const rubric = rubrics.find(r => r.id === rubricId)

  return (
    <div className="home">
      <section className="hero">
        <h1>Mark a script.</h1>
        <p className="lede">Drop the scanned pages of one answer sheet. Each answer is read, scored against
          your rubric by meaning, and flagged when the machine isn't sure.</p>
      </section>

      <section className="panel compose">
        <DropZone files={files} onChange={setFiles} />

        <div className="compose-bar">
          <label className="field">
            <span>Rubric</span>
            <select value={rubricId} onChange={e => setRubricId(e.target.value)}>
              {rubrics.length === 0 && <option value="">No rubrics yet</option>}
              {rubrics.map(r => <option key={r.id} value={r.id}>{r.subject}</option>)}
            </select>
          </label>
          {rubric && <span className="muted small">{rubric.n_questions} questions · {rubric.total_marks} marks</span>}
          <button className="btn primary" disabled={!files.length || !rubricId || busy} onClick={submit}>
            {busy ? 'Uploading…' : `Evaluate ${files.length ? files.length + ' page' + (files.length > 1 ? 's' : '') : ''}`}
          </button>
        </div>
        {error && <p className="error">{error}</p>}
      </section>

      {history.length > 0 && (
        <section className="history">
          <h2>Recent</h2>
          <ul>
            {history.map(e => (
              <li key={e.id}>
                <a href={`#/e/${e.id}`} className="history-row">
                  <span className="h-subject">{e.subject}</span>
                  <span className="muted small">{new Date(e.created_at).toLocaleString()} · {e.filenames.length} file(s)</span>
                  <span className="h-status">
                    {e.status === 'done' && e.total_score != null
                      ? <>
                          <ScoreMark score={e.total_score} max={e.total_marks ?? 0} small />
                          {!!e.low_count && <span className="pill low">{e.low_count} to review</span>}
                        </>
                      : <span className={`pill ${e.status === 'error' ? 'low' : 'medium'}`}>{e.status}</span>}
                  </span>
                </a>
                <button className="icon-btn" title="Delete" onClick={() => remove(e.id)}>×</button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
