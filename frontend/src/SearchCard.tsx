import { useEffect, useRef, useState } from 'react'
import { CABIN_LABEL, dayLabel, shiftDate } from './format'
import type { Cabin, SearchParams } from './types'

interface Airport { code: string; city: string; name: string; country: string }

interface Props {
  initial: SearchParams
  cabin: Cabin | 'any'
  onCabin: (c: Cabin | 'any') => void
  busy: boolean
  onSearch: (p: SearchParams) => void
}

const box = 'h-14 w-full rounded border border-line bg-raise px-4 text-base outline-none hover:border-sub focus:border-brand focus:ring-1 focus:ring-brand'
const mini = 'rounded bg-transparent px-2 py-1.5 text-sm text-sub hover:bg-hover outline-none focus:ring-1 focus:ring-brand'

function AirportField({ label, code, onCode }: { label: string; code: string; onCode: (c: string) => void }) {
  const [text, setText] = useState(code)
  const [items, setItems] = useState<Airport[]>([])
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const wrap = useRef<HTMLDivElement>(null)

  // Show "City (CODE)" for the current code when the field is not being edited.
  useEffect(() => {
    if (!code) return
    let live = true
    fetch(`/api/airports/lookup?codes=${code}`).then((r) => r.json()).then((d) => {
      if (live && d[code]) setText(`${d[code].city} (${code})`)
    }).catch(() => {})
    return () => { live = false }
  }, [code])

  useEffect(() => {
    if (!open || !text.trim() || /\(\w{3}\)$/.test(text)) return
    const t = setTimeout(() => {
      fetch(`/api/airports?q=${encodeURIComponent(text.trim())}`).then((r) => r.json()).then((d) => { setItems(Array.isArray(d) ? d : []); setActive(0) }).catch(() => {})
    }, 120)
    return () => clearTimeout(t)
  }, [text, open])

  useEffect(() => {
    const close = (e: MouseEvent) => !wrap.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])

  const pick = (a: Airport) => { onCode(a.code); setText(`${a.city} (${a.code})`); setOpen(false) }

  return (
    <div ref={wrap} className="relative">
      <input className={box} aria-label={label} placeholder={label} value={text} required
        onFocus={(e) => { e.target.select(); setOpen(true) }}
        onChange={(e) => {
          setText(e.target.value); setOpen(true)
          const v = e.target.value.trim().toUpperCase()
          if (/^[A-Z]{3}$/.test(v)) onCode(v)
        }}
        onKeyDown={(e) => {
          if (!open || !items.length) return
          if (e.key === 'ArrowDown') { e.preventDefault(); setActive((active + 1) % items.length) }
          if (e.key === 'ArrowUp') { e.preventDefault(); setActive((active - 1 + items.length) % items.length) }
          if (e.key === 'Enter') { e.preventDefault(); pick(items[active]) }
          if (e.key === 'Escape') setOpen(false)
        }} />
      {open && items.length > 0 && (
        <ul className="absolute z-30 mt-1 w-full min-w-72 overflow-hidden rounded-lg border border-line bg-raise py-1 shadow-lg">
          {items.map((a, i) => (
            <li key={a.code}>
              <button type="button" onMouseDown={(e) => { e.preventDefault(); pick(a) }}
                className={`flex w-full items-center gap-3 px-4 py-2 text-left ${i === active ? 'bg-hover' : ''}`}>
                <span className="w-10 font-medium">{a.code}</span>
                <span className="min-w-0 flex-1 truncate">{a.city} <span className="text-sm text-sub">· {a.name}, {a.country}</span></span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function SearchCard({ initial, cabin, onCabin, busy, onSearch }: Props) {
  const [p, setP] = useState<SearchParams>(initial)
  const [swapKey, setSwapKey] = useState(0)

  return (
    <form className="relative rounded-lg bg-raise px-4 pt-2 pb-10 shadow-[0_1px_3px_rgb(60_64_67/0.3),0_4px_8px_3px_rgb(60_64_67/0.15)] sm:px-6"
      onSubmit={(e) => { e.preventDefault(); onSearch(p) }}>
      <div className="mb-2 flex flex-wrap items-center gap-1">
        <span className={mini + ' cursor-default'}>One way</span>
        <select className={mini} aria-label="Cabin" value={cabin} onChange={(e) => onCabin(e.target.value as Cabin | 'any')}>
          <option value="any">Any cabin</option>
          {(['economy', 'premium', 'business', 'first'] as Cabin[]).map((c) => <option key={c} value={c}>{CABIN_LABEL[c]}</option>)}
        </select>
        <select className={mini} aria-label="Date range" value={p.flex} onChange={(e) => setP({ ...p, flex: Number(e.target.value) })}>
          <option value={0}>Exact date</option>
          <option value={1}>± 1 day</option>
          <option value={2}>± 2 days</option>
          <option value={3}>± 3 days</option>
        </select>
      </div>

      <div className="grid gap-3 md:grid-cols-[1fr_1fr_1.1fr]">
        <div className="relative grid grid-cols-2 gap-3 md:col-span-2">
          <AirportField key={'o' + swapKey} label="Where from?" code={p.origin} onCode={(c) => setP((s) => ({ ...s, origin: c }))} />
          <AirportField key={'d' + swapKey} label="Where to?" code={p.destination} onCode={(c) => setP((s) => ({ ...s, destination: c }))} />
          <button type="button" aria-label="Swap origin and destination"
            onClick={() => { setP({ ...p, origin: p.destination, destination: p.origin }); setSwapKey(swapKey + 1) }}
            className="absolute top-1/2 left-1/2 z-10 flex h-9 w-9 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border border-line bg-raise text-sub hover:bg-hover">
            ⇄
          </button>
        </div>
        <div className={box + ' flex items-center gap-1 !px-2'}>
          <input type="date" aria-label="Departure" className="min-w-0 flex-1 bg-transparent px-2 outline-none" value={p.date} required
            onChange={(e) => setP({ ...p, date: e.target.value })} />
          <span className="hidden text-sm text-sub lg:inline">{p.date && dayLabel(p.date).split(' ')[0]}</span>
          <button type="button" aria-label="Day before" className="h-9 w-9 rounded-full text-sub hover:bg-hover" onClick={() => setP({ ...p, date: shiftDate(p.date, -1) })}>‹</button>
          <button type="button" aria-label="Day after" className="h-9 w-9 rounded-full text-sub hover:bg-hover" onClick={() => setP({ ...p, date: shiftDate(p.date, 1) })}>›</button>
        </div>
      </div>

      <button type="submit" disabled={busy}
        className="absolute -bottom-5 left-1/2 flex h-10 -translate-x-1/2 items-center gap-2 rounded-full bg-brand px-6 font-medium text-page shadow-md hover:brightness-110 disabled:opacity-70">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        {busy ? 'Searching' : 'Search'}
      </button>
    </form>
  )
}
