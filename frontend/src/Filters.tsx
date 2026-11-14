import { useEffect, useRef, useState, type ReactNode } from 'react'
import type { Method } from './types'

export interface FilterState {
  maxStops: number
  methods: Method[]
  programs: string[] // empty: all
  airlines: string[] // empty: all
  maxHours: number // 0: any
  maxAgeDays: number // 0: any
  centsPerMile: number
}

export const DEFAULT_FILTERS: FilterState = {
  maxStops: 9, methods: ['cash', 'award', 'joined'], programs: [], airlines: [], maxHours: 0, maxAgeDays: 0, centsPerMile: 1.2,
}

function Chip({ label, active, children, onClear }: { label: string; active: boolean; children: ReactNode; onClear?: () => void }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const close = (e: MouseEvent) => !ref.current?.contains(e.target as Node) && setOpen(false)
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [])
  return (
    <div ref={ref} className="relative shrink-0">
      <button type="button" aria-expanded={open} onClick={() => setOpen(!open)}
        className={`flex h-8 items-center gap-1.5 rounded-lg border px-3 text-sm ${
          active ? 'border-transparent bg-brand-soft text-brand' : 'border-line text-ink hover:bg-hover'
        }`}>
        {label}
        {active && onClear ? (
          <span role="button" aria-label={`Clear ${label}`} className="-mr-1 rounded-full px-1 hover:bg-hover"
            onClick={(e) => { e.stopPropagation(); onClear() }}>✕</span>
        ) : (
          <span className="text-[10px] text-sub">▼</span>
        )}
      </button>
      {open && (
        <div className="absolute left-0 z-20 mt-2 w-72 rounded-lg border border-line bg-raise p-4 shadow-lg">{children}</div>
      )}
    </div>
  )
}

const Row = ({ children }: { children: ReactNode }) => <label className="flex cursor-pointer items-center gap-3 py-1.5 text-sm">{children}</label>

function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v]
}

interface Props {
  f: FilterState
  set: (f: FilterState) => void
  programs: [string, string][]
  airlines: [string, string][]
  hasCash: boolean
}

const METHOD_LABEL: Record<Method, string> = { cash: 'Cash fares', award: 'Awards (one booking)', joined: 'Joined award legs' }

export function Filters({ f, set, programs, airlines, hasCash }: Props) {
  const stopsLabel = f.maxStops === 0 ? 'Nonstop only' : f.maxStops === 1 ? '1 stop or fewer' : f.maxStops === 2 ? '2 stops or fewer' : 'Stops'
  const methodsActive = f.methods.length < 3
  return (
    <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0">
      <Chip label={methodsActive ? f.methods.map((m) => METHOD_LABEL[m].split(' ')[0]).join(', ') || 'No type' : 'Pay with'} active={methodsActive}
        onClear={() => set({ ...f, methods: DEFAULT_FILTERS.methods })}>
        <p className="mb-2 font-medium">Pay with</p>
        {(['cash', 'award', 'joined'] as Method[]).map((m) => (
          <Row key={m}>
            <input type="checkbox" checked={f.methods.includes(m)} onChange={() => set({ ...f, methods: toggle(f.methods, m) })} />
            {METHOD_LABEL[m]}
            {m === 'cash' && !hasCash && <span className="text-xs text-sub">(no data)</span>}
          </Row>
        ))}
      </Chip>

      <Chip label={stopsLabel} active={f.maxStops < 9} onClear={() => set({ ...f, maxStops: 9 })}>
        <p className="mb-2 font-medium">Stops</p>
        {[[9, 'Any number of stops'], [0, 'Nonstop only'], [1, '1 stop or fewer'], [2, '2 stops or fewer']].map(([v, l]) => (
          <Row key={v}><input type="radio" name="stops" checked={f.maxStops === v} onChange={() => set({ ...f, maxStops: v as number })} />{l}</Row>
        ))}
      </Chip>

      <Chip label={f.programs.length ? `${f.programs.length} program${f.programs.length > 1 ? 's' : ''}` : 'Programs'} active={f.programs.length > 0}
        onClear={() => set({ ...f, programs: [] })}>
        <p className="mb-2 font-medium">Loyalty programs</p>
        <div className="max-h-64 overflow-y-auto">
          {programs.map(([id, name]) => (
            <Row key={id}><input type="checkbox" checked={f.programs.includes(id)} onChange={() => set({ ...f, programs: toggle(f.programs, id) })} />{name}</Row>
          ))}
        </div>
      </Chip>

      <Chip label={f.airlines.length ? `${f.airlines.length} airline${f.airlines.length > 1 ? 's' : ''}` : 'Airlines'} active={f.airlines.length > 0}
        onClear={() => set({ ...f, airlines: [] })}>
        <p className="mb-2 font-medium">Airlines</p>
        <div className="max-h-64 overflow-y-auto">
          {airlines.map(([code, name]) => (
            <Row key={code}><input type="checkbox" checked={f.airlines.includes(code)} onChange={() => set({ ...f, airlines: toggle(f.airlines, code) })} />{name}</Row>
          ))}
        </div>
      </Chip>

      <Chip label={f.maxHours ? `Under ${f.maxHours} hr` : 'Duration'} active={f.maxHours > 0} onClear={() => set({ ...f, maxHours: 0 })}>
        <p className="mb-2 font-medium">Flight duration · {f.maxHours ? `under ${f.maxHours} hr` : 'any'}</p>
        <input type="range" min={4} max={31} value={f.maxHours || 31} className="w-full"
          onChange={(e) => set({ ...f, maxHours: Number(e.target.value) >= 31 ? 0 : Number(e.target.value) })} />
      </Chip>

      <Chip label={f.maxAgeDays ? `Checked in last ${f.maxAgeDays} d` : 'Data age'} active={f.maxAgeDays > 0} onClear={() => set({ ...f, maxAgeDays: 0 })}>
        <p className="mb-2 font-medium">Award data age</p>
        {[[0, 'Any age'], [1, 'Last 24 hours'], [3, 'Last 3 days'], [7, 'Last 7 days']].map(([v, l]) => (
          <Row key={v}><input type="radio" name="age" checked={f.maxAgeDays === v} onChange={() => set({ ...f, maxAgeDays: v as number })} />{l}</Row>
        ))}
      </Chip>

      <Chip label={`Miles at ${f.centsPerMile}¢`} active={f.centsPerMile !== DEFAULT_FILTERS.centsPerMile}
        onClear={() => set({ ...f, centsPerMile: DEFAULT_FILTERS.centsPerMile })}>
        <p className="mb-1 font-medium">Value of one mile · {f.centsPerMile.toFixed(1)}¢</p>
        <p className="mb-2 text-xs text-sub">Used to rank awards against cash fares.</p>
        <input type="range" min={0.5} max={3} step={0.1} value={f.centsPerMile} className="w-full"
          onChange={(e) => set({ ...f, centsPerMile: Number(e.target.value) })} />
      </Chip>
    </div>
  )
}
