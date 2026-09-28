import type { Confidence, Verdict } from '../api'

/** Examiner-style score in red pen: 2½/4 */
export function fmt(n: number) {
  const whole = Math.floor(n)
  const half = Math.abs(n - whole - 0.5) < 0.01
  if (half) return whole === 0 ? '½' : `${whole}½`
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

export function ScoreMark({ score, max, small }: { score: number; max: number; small?: boolean }) {
  return (
    <span className={`score-mark ${small ? 'sm' : ''}`} aria-label={`${score} out of ${max}`}>
      <span className="num">{fmt(score)}</span>
      <span className="den">/{fmt(max)}</span>
    </span>
  )
}

const GLYPH: Record<Verdict, string> = { met: '✓', partial: '½', not_met: '✗' }
export function VerdictGlyph({ v }: { v: Verdict }) {
  return <span className={`glyph ${v}`}>{GLYPH[v]}</span>
}

const LABEL: Record<Confidence, string> = { high: 'High confidence', medium: 'Medium', low: 'Needs review' }
export function ConfidencePill({ level }: { level: Confidence }) {
  return <span className={`pill ${level}`}><i />{LABEL[level]}</span>
}
