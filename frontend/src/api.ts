export type Verdict = 'met' | 'partial' | 'not_met'
export type Confidence = 'high' | 'medium' | 'low'

export interface Criterion { id: string; desc: string; marks: number; needs_diagram?: boolean }
export interface RubricQuestion {
  qno: string; question: string; max_marks: number; model_answer: string
  criteria: Criterion[]; diagram_expected?: boolean
}
export interface Rubric { id: string; subject: string; total_marks: number; questions: RubricQuestion[] }
export interface RubricSummary { id: string; subject: string; total_marks: number; n_questions: number }

export interface RawLine {
  text: string; crossed_out: boolean; margin_note: boolean; is_diagram: boolean
  legibility: 'high' | 'medium' | 'low'; page: number
}
export interface CriterionResult {
  id: string; desc: string; marks: number; awarded: number; verdict: Verdict; evidence: string; agreement: number
}
export interface Answer {
  question_no: string; question: string; pages: number[]; extracted_text: string; raw_lines: RawLine[]
  score: number; max_marks: number; score_vs_key: string; criteria: CriterionResult[]
  judge_run_scores: number[]; embedding_similarity: number | null; embedding_score: number | null
  ocr_agreement: number | null; confidence: Confidence; reason: string; signals: string[]; comment: string
}
export interface Result {
  rubric_id: string; subject: string; pages: number; total_score: number; total_marks: number
  elapsed_s: number; models_used: Record<string, string>; answers: Answer[]
}
export interface Evaluation {
  id: string; rubric_id: string; subject: string; status: 'queued' | 'running' | 'done' | 'error'
  stage: string; detail: string; filenames: string[]; page_count: number
  total_score: number | null; total_marks: number | null; low_count: number | null
  elapsed_s: number | null; error: string | null; created_at: string
  pages?: string[]; result?: Result | null
}

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init)
  if (!r.ok) {
    let msg = `${r.status} ${r.statusText}`
    try { const j = await r.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* not json */ }
    throw new Error(msg)
  }
  return r.json()
}

const json = (body: unknown): RequestInit => ({
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
})

export const api = {
  rubrics: () => req<RubricSummary[]>('/api/rubrics'),
  rubric: (id: string) => req<Rubric>(`/api/rubrics/${encodeURIComponent(id)}`),
  saveRubric: (r: Rubric) => req<Rubric>(`/api/rubrics/${encodeURIComponent(r.id)}`, json(r)),
  deleteRubric: (id: string) => req(`/api/rubrics/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  evaluations: () => req<Evaluation[]>('/api/evaluations'),
  evaluation: (id: string) => req<Evaluation>(`/api/evaluations/${id}`),
  deleteEvaluation: (id: string) => req(`/api/evaluations/${id}`, { method: 'DELETE' }),
  evaluate: (rubricId: string, files: File[]) => {
    const fd = new FormData()
    fd.append('rubric_id', rubricId)
    files.forEach(f => fd.append('files', f))
    return req<{ id: string }>('/api/evaluations', { method: 'POST', body: fd })
  },
  exportUrl: (id: string, fmt: 'json' | 'csv') => `/api/evaluations/${id}/export?fmt=${fmt}`,
}
