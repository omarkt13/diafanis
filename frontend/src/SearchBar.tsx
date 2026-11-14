import { useState } from 'react'
import type { SearchParams } from './types'

interface Props {
  initial: SearchParams
  busy: boolean
  onSearch: (p: SearchParams) => void
}

const field =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-base outline-none focus:border-sky-500 focus:ring-2 focus:ring-sky-500/30 dark:border-slate-700 dark:bg-slate-900'

export function SearchBar({ initial, busy, onSearch }: Props) {
  const [p, setP] = useState<SearchParams>(initial)
  const set = (k: keyof SearchParams, v: string | number) => setP({ ...p, [k]: v })

  return (
    <form
      className="grid grid-cols-2 gap-3 rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200 sm:grid-cols-[1fr_auto_1fr_1fr_auto_auto] sm:items-end dark:bg-slate-900 dark:ring-slate-800"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch({ ...p, origin: p.origin.trim().toUpperCase(), destination: p.destination.trim().toUpperCase() })
      }}
    >
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-500">From</span>
        <input className={field + ' uppercase'} value={p.origin} maxLength={3} required placeholder="DXB"
          onChange={(e) => set('origin', e.target.value)} />
      </label>
      <button type="button" aria-label="Swap origin and destination"
        className="hidden h-11 w-11 items-center justify-center rounded-full text-slate-500 hover:bg-slate-100 sm:flex dark:hover:bg-slate-800"
        onClick={() => setP({ ...p, origin: p.destination, destination: p.origin })}>
        ⇄
      </button>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-500">To</span>
        <input className={field + ' uppercase'} value={p.destination} maxLength={3} required placeholder="GVA"
          onChange={(e) => set('destination', e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-500">Date</span>
        <input type="date" className={field} value={p.date} required onChange={(e) => set('date', e.target.value)} />
      </label>
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-500">Flexible</span>
        <select className={field} value={p.flex} onChange={(e) => set('flex', Number(e.target.value))}>
          <option value={0}>Exact</option>
          <option value={1}>± 1 day</option>
          <option value={2}>± 2 days</option>
          <option value={3}>± 3 days</option>
        </select>
      </label>
      <button type="submit" disabled={busy}
        className="col-span-2 h-11 rounded-full bg-sky-600 px-6 font-medium text-white hover:bg-sky-700 disabled:opacity-60 sm:col-span-1">
        {busy ? 'Searching…' : 'Search'}
      </button>
    </form>
  )
}
