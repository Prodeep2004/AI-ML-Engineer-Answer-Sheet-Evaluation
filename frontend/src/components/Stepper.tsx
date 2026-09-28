const STAGES = [
  { key: 'extract', label: 'Extract', hint: 'Reading handwriting twice, independently' },
  { key: 'structure', label: 'Structure', hint: 'Splitting the script by question' },
  { key: 'score', label: 'Score', hint: 'Grading each rubric point by meaning' },
  { key: 'confidence', label: 'Confidence', hint: 'Flagging what a human should check' },
]

export default function Stepper({ stage, detail }: { stage: string; detail: string }) {
  const at = Math.max(0, STAGES.findIndex(s => s.key === stage))
  return (
    <ol className="stepper">
      {STAGES.map((s, i) => (
        <li key={s.key} className={i < at ? 'done' : i === at ? 'now' : ''}>
          <span className="dot">{i < at ? '✓' : i + 1}</span>
          <span className="st-label">{s.label}</span>
          <span className="st-hint">{i === at ? detail || s.hint : s.hint}</span>
        </li>
      ))}
    </ol>
  )
}
