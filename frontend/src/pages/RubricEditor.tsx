import { useEffect, useState } from 'react'
import { api, type Criterion, type Rubric, type RubricQuestion } from '../api'

const blankQuestion = (n: number): RubricQuestion => ({
  qno: `Q${n}`, question: '', max_marks: 1, model_answer: '',
  criteria: [{ id: 'c1', desc: '', marks: 1 }], diagram_expected: false,
})

export default function RubricEditor({ id }: { id: string }) {
  const isNew = id === 'new'
  const [r, setR] = useState<Rubric | null>(
    isNew ? { id: '', subject: '', total_marks: 0, questions: [blankQuestion(1)] } : null,
  )
  const [mode, setMode] = useState<'form' | 'json'>('form')
  const [jsonText, setJsonText] = useState('')
  const [msg, setMsg] = useState<{ kind: 'ok' | 'error'; text: string } | null>(null)

  useEffect(() => { if (!isNew) api.rubric(id).then(setR).catch(e => setMsg({ kind: 'error', text: e.message })) }, [id, isNew])

  if (!r) return <div className="loading">{msg?.text ?? 'Loading…'}</div>

  const setQ = (i: number, patch: Partial<RubricQuestion>) =>
    setR({ ...r, questions: r.questions.map((q, k) => (k === i ? { ...q, ...patch } : q)) })
  const setC = (qi: number, ci: number, patch: Partial<Criterion>) => {
    const q = r.questions[qi]
    const criteria = q.criteria.map((c, k) => (k === ci ? { ...c, ...patch } : c))
    setQ(qi, { criteria, max_marks: criteria.reduce((s, c) => s + (Number(c.marks) || 0), 0) })
  }
  const total = r.questions.reduce((s, q) => s + q.max_marks, 0)

  const switchMode = (m: 'form' | 'json') => {
    if (m === 'json') setJsonText(JSON.stringify({ ...r, total_marks: total }, null, 2))
    else {
      try { setR(JSON.parse(jsonText)); setMsg(null) } catch (e) { setMsg({ kind: 'error', text: `Invalid JSON: ${(e as Error).message}` }); return }
    }
    setMode(m)
  }

  const save = async () => {
    let body: Rubric
    try { body = mode === 'json' ? JSON.parse(jsonText) : { ...r, total_marks: total } }
    catch (e) { setMsg({ kind: 'error', text: `Invalid JSON: ${(e as Error).message}` }); return }
    if (!body.id.trim()) { setMsg({ kind: 'error', text: 'Give the rubric an id (e.g. physics-unit-2).' }); return }
    try {
      const saved = await api.saveRubric(body)
      setR(saved); setMsg({ kind: 'ok', text: 'Saved.' })
      if (isNew) location.hash = `#/rubrics/${encodeURIComponent(saved.id)}`
    } catch (e) { setMsg({ kind: 'error', text: (e as Error).message }) }
  }

  const remove = async () => {
    if (!confirm(`Delete rubric "${r.subject || r.id}"?`)) return
    await api.deleteRubric(r.id)
    location.hash = '#/rubrics'
  }

  return (
    <div className="editor">
      <div className="eval-head">
        <div>
          <a href="#/rubrics" className="back">← Rubrics</a>
          <h1>{isNew ? 'New rubric' : r.subject || r.id}</h1>
          <p className="muted small">{r.questions.length} questions · {total} marks</p>
        </div>
        <div className="row">
          <div className="tabs">
            <button className={mode === 'form' ? 'on' : ''} onClick={() => switchMode('form')}>Form</button>
            <button className={mode === 'json' ? 'on' : ''} onClick={() => switchMode('json')}>JSON</button>
          </div>
          <button className="btn primary" onClick={save}>Save</button>
        </div>
      </div>
      {msg && <p className={msg.kind === 'ok' ? 'ok' : 'error'}>{msg.text}</p>}

      {mode === 'json' ? (
        <textarea className="json-area" value={jsonText} onChange={e => setJsonText(e.target.value)} spellCheck={false} />
      ) : (
        <>
          <section className="panel grid2">
            <label className="field"><span>Subject</span>
              <input value={r.subject} onChange={e => setR({ ...r, subject: e.target.value })} placeholder="Physics — Unit 2" />
            </label>
            <label className="field"><span>Id</span>
              <input value={r.id} disabled={!isNew} onChange={e => setR({ ...r, id: e.target.value.trim().toLowerCase().replace(/\s+/g, '-') })} placeholder="physics-unit-2" />
            </label>
          </section>

          {r.questions.map((q, qi) => (
            <section className="panel qedit" key={qi}>
              <div className="qedit-head">
                <input className="qno-input" value={q.qno} onChange={e => setQ(qi, { qno: e.target.value.toUpperCase() })} />
                <span className="muted small">{q.max_marks} marks</span>
                <label className="check"><input type="checkbox" checked={!!q.diagram_expected} onChange={e => setQ(qi, { diagram_expected: e.target.checked })} /> diagram expected</label>
                <button className="icon-btn" title="Remove question" onClick={() => setR({ ...r, questions: r.questions.filter((_, k) => k !== qi) })}>×</button>
              </div>
              <label className="field"><span>Question</span>
                <textarea rows={2} value={q.question} onChange={e => setQ(qi, { question: e.target.value })} />
              </label>
              <label className="field"><span>Model answer</span>
                <textarea rows={3} value={q.model_answer} onChange={e => setQ(qi, { model_answer: e.target.value })} />
              </label>
              <div className="field"><span>Mark-bearing points</span>
                {q.criteria.map((c, ci) => (
                  <div className="crit-row" key={ci}>
                    <span className="mono muted">{c.id}</span>
                    <input value={c.desc} placeholder="What must the answer contain?" onChange={e => setC(qi, ci, { desc: e.target.value })} />
                    <input type="number" min={0} step={0.5} value={c.marks} onChange={e => setC(qi, ci, { marks: Number(e.target.value) })} />
                    <label className="check" title="Mark depends on a diagram"><input type="checkbox" checked={!!c.needs_diagram} onChange={e => setC(qi, ci, { needs_diagram: e.target.checked })} />◇</label>
                    <button className="icon-btn" onClick={() => {
                      const criteria = q.criteria.filter((_, k) => k !== ci)
                      setQ(qi, { criteria, max_marks: criteria.reduce((s, x) => s + x.marks, 0) })
                    }}>×</button>
                  </div>
                ))}
                <button className="link" onClick={() => {
                  const criteria = [...q.criteria, { id: `c${q.criteria.length + 1}`, desc: '', marks: 1 }]
                  setQ(qi, { criteria, max_marks: criteria.reduce((s, x) => s + x.marks, 0) })
                }}>+ add point</button>
              </div>
            </section>
          ))}
          <div className="row">
            <button className="btn ghost" onClick={() => setR({ ...r, questions: [...r.questions, blankQuestion(r.questions.length + 1)] })}>+ Add question</button>
            {!isNew && <button className="btn danger" onClick={remove}>Delete rubric</button>}
          </div>
        </>
      )}
    </div>
  )
}
