import { useEffect, useState } from 'react'
import { AwardResults } from './AwardResults'
import { CashResults } from './CashResults'
import { SearchBar } from './SearchBar'
import type { AwardSearchResult, SearchParams } from './types'

type Tab = 'awards' | 'cash'

function fromUrl(): SearchParams | null {
  const q = new URLSearchParams(window.location.search)
  const origin = q.get('from')
  const destination = q.get('to')
  const date = q.get('date')
  if (!origin || !destination || !date) return null
  return { origin, destination, date, flex: Number(q.get('flex') ?? 1) }
}

function toUrl(p: SearchParams) {
  const q = new URLSearchParams({ from: p.origin, to: p.destination, date: p.date, flex: String(p.flex) })
  window.history.replaceState(null, '', `?${q}`)
}

export default function App() {
  const initial = fromUrl()
  const [search, setSearch] = useState<SearchParams | null>(initial)
  const [tab, setTab] = useState<Tab>('awards')
  const [awards, setAwards] = useState<AwardSearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!search) return
    toUrl(search)
    const ctl = new AbortController()
    setBusy(true)
    setError(null)
    const q = new URLSearchParams({ origin: search.origin, destination: search.destination, date: search.date, flex: String(search.flex) })
    fetch(`/api/awards?${q}`, { signal: ctl.signal })
      .then(async (r) => {
        const body = await r.json()
        if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : r.statusText)
        setAwards(body)
      })
      .catch((e) => e.name !== 'AbortError' && setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
    return () => ctl.abort()
  }, [search])

  const tabClass = (t: Tab) =>
    `border-b-2 px-1 pb-2 text-sm font-medium ${
      tab === t ? 'border-sky-600 text-sky-700 dark:text-sky-300' : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
    }`

  return (
    <div className="mx-auto max-w-5xl space-y-5 px-4 py-6">
      <header className="flex items-baseline justify-between">
        <h1 className="text-xl font-semibold tracking-tight">Waypoint</h1>
        {awards?.rate_limit_remaining != null && (
          <span className="text-xs text-slate-500">Seats.aero calls left today: {awards.rate_limit_remaining}</span>
        )}
      </header>

      <SearchBar
        initial={initial ?? { origin: 'DXB', destination: 'GVA', date: '2026-11-20', flex: 1 }}
        busy={busy}
        onSearch={setSearch}
      />

      {search && (
        <nav className="flex gap-6 border-b border-slate-200 dark:border-slate-800">
          <button className={tabClass('awards')} onClick={() => setTab('awards')}>Award seats</button>
          <button className={tabClass('cash')} onClick={() => setTab('cash')}>Cash fares</button>
        </nav>
      )}

      {error && <p className="rounded-lg bg-rose-50 p-4 text-rose-900 dark:bg-rose-950 dark:text-rose-200">{error}</p>}
      {busy && !awards && <p className="text-slate-500">Searching award seats…</p>}

      {tab === 'awards' && awards && (
        <>
          <AwardResults key={`${awards.origin}${awards.destination}${awards.dates.join()}`} result={awards} />
          <p className="text-xs text-slate-500">
            {awards.options.length} options · {awards.api_calls} API calls · hubs checked for joined legs: {awards.hubs.join(', ')}
          </p>
        </>
      )}
      {tab === 'cash' && search && <CashResults search={search} />}
    </div>
  )
}
