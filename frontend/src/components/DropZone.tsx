import { useEffect, useMemo, useRef, useState } from 'react'

const ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff'
const natural = (a: File, b: File) => a.name.localeCompare(b.name, undefined, { numeric: true })

export default function DropZone({ files, onChange }: { files: File[]; onChange: (f: File[]) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [over, setOver] = useState(false)

  const add = (list: FileList | null) => {
    if (!list) return
    const incoming = Array.from(list).filter(f => /\.(pdf|jpe?g|png|webp|bmp|tiff?)$/i.test(f.name))
    const seen = new Set(files.map(f => f.name + f.size))
    onChange([...files, ...incoming.filter(f => !seen.has(f.name + f.size))].sort(natural))
  }

  const previews = useMemo(
    () => files.map(f => (f.type.startsWith('image/') ? URL.createObjectURL(f) : '')),
    [files],
  )
  useEffect(() => () => previews.forEach(u => u && URL.revokeObjectURL(u)), [previews])

  const move = (i: number, d: number) => {
    const j = i + d
    if (j < 0 || j >= files.length) return
    const next = [...files]
    ;[next[i], next[j]] = [next[j], next[i]]
    onChange(next)
  }

  return (
    <div>
      <div
        className={`drop ${over ? 'over' : ''} ${files.length ? 'has' : ''}`}
        onDragOver={e => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={e => { e.preventDefault(); setOver(false); add(e.dataTransfer.files) }}
        onClick={() => input.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && input.current?.click()}
      >
        <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={e => { add(e.target.files); e.target.value = '' }} />
        <div className="drop-mark">↓</div>
        <div className="drop-title">Drop answer pages here</div>
        <div className="muted small">JPG, PNG or PDF · in page order · or click to browse</div>
      </div>

      {files.length > 0 && (
        <ol className="thumbs">
          {files.map((f, i) => (
            <li key={f.name + f.size} className="thumb">
              {previews[i] ? <img src={previews[i]} alt="" /> : <div className="thumb-pdf">PDF</div>}
              <span className="thumb-no">{i + 1}</span>
              <span className="thumb-name" title={f.name}>{f.name}</span>
              <span className="thumb-actions">
                <button onClick={() => move(i, -1)} disabled={i === 0} title="Move earlier">‹</button>
                <button onClick={() => move(i, 1)} disabled={i === files.length - 1} title="Move later">›</button>
                <button onClick={() => onChange(files.filter((_, k) => k !== i))} title="Remove">×</button>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
