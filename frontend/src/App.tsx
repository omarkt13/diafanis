import { useEffect, useMemo, useState } from 'react'
import { airlineName } from './airlines'
import { DEFAULT_FILTERS, Filters, type FilterState } from './Filters'
import { CABIN_LABEL, dayLabel, miles, usd } from './format'
import { SearchCard } from './SearchCard'
import type { AwardSearchResult, Cabin, CashAll, Places, SearchParams, Way } from './types'
import { buildFinds, buildWays, type Find } from './ways'
import { WayRow } from './WayRow'

type SortTab = 'best' | 'cheapest'
const PAGE = 12

function fromUrl(): SearchParams | null {
  const q = new URLSearchParams(window.location.search)
  const origin = q.get('from'), destination = q.get('to'), date = q.get('date')
  if (!origin || !destination || !date) return null
  return { origin, destination, date, flex: Number(q.get('flex') ?? 1) }
}

function stored<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(key)
    return v ? (JSON.parse(v) as T) : fallback
  } catch {
    return fallback
  }
}
function store(key: string, v: unknown) {
  try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode */ }
}

const FIND_TONE = { good: 'text-good', award: 'text-award', brand: 'text-brand' }

export default function App() {
  const initial = useMemo(fromUrl, [])
  const [search, setSearch] = useState<SearchParams | null>(initial)
  const [cabin, setCabin] = useState<Cabin | 'any'>(() => stored('cabin', 'business'))
  const [awards, setAwards] = useState<AwardSearchResult | null>(null)
  const [cash, setCash] = useState<CashAll | null>(null)
  const [cashNote, setCashNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [day, setDay] = useState<string>(initial?.date ?? '')
  const [filters, setFilters] = useState<FilterState>(() => ({ ...DEFAULT_FILTERS, centsPerMile: stored('cpm', DEFAULT_FILTERS.centsPerMile) }))
  const [tab, setTab] = useState<SortTab>('best')
  const [openId, setOpenId] = useState<string | null>(null)
  const [shown, setShown] = useState(PAGE)
  const [places, setPlaces] = useState<Places>({})

  useEffect(() => store('cabin', cabin), [cabin])
  useEffect(() => store('cpm', filters.centsPerMile), [filters.centsPerMile])

  useEffect(() => {
    if (!search) return
    const q = new URLSearchParams({ from: search.origin, to: search.destination, date: search.date, flex: String(search.flex) })
    window.history.replaceState(null, '', `?${q}`)
    const ctl = new AbortController()
    const api = new URLSearchParams({ origin: search.origin, destination: search.destination, date: search.date })
    setBusy(true); setError(null); setAwards(null); setCash(null); setCashNote(null); setDay(search.date); setOpenId(null); setShown(PAGE)

    const get = async (url: string) => {
      const r = await fetch(url, { signal: ctl.signal })
      const body = await r.json()
      if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : r.statusText)
      return body
    }
    // One search fans out to both sources; the page merges them into one list.
    const a = get(`/api/awards?${api}&flex=${search.flex}`).then(setAwards).catch((e) => e.name !== 'AbortError' && setError(e.message))
    const c = get(`/api/cash/all?${api}`).then(setCash).catch((e) => e.name !== 'AbortError' && setCashNote(e.message))
    Promise.allSettled([a, c]).then(() => !ctl.signal.aborted && setBusy(false))
    return () => ctl.abort()
  }, [search])

  const ways = useMemo(() => buildWays(awards, cash, search?.date ?? '', filters.centsPerMile), [awards, cash, search, filters.centsPerMile])

  useEffect(() => {
    const codes = new Set<string>()
    for (const w of ways) {
      w.award?.legs.forEach((l) => [l.origin, l.destination, ...l.connections].forEach((c) => codes.add(c)))
      w.cash?.segments.forEach((s) => { codes.add(s.origin); codes.add(s.destination) })
    }
    const missing = [...codes].filter((c) => !places[c])
    if (!missing.length) return
    fetch(`/api/airports/lookup?codes=${missing.join(',')}`).then((r) => r.json()).then((d) => setPlaces((p) => ({ ...p, ...d }))).catch(() => {})
  }, [ways]) // eslint-disable-line react-hooks/exhaustive-deps

  const dates = awards?.dates ?? (search ? [search.date] : [])
  const programs = useMemo(() => [...new Map(ways.filter((w) => w.award).map((w) => [w.award!.program, w.award!.program_name])).entries()].sort((a, b) => a[1].localeCompare(b[1])), [ways])
  const airlines = useMemo(() => [...new Set(ways.flatMap((w) => w.carriers))].map((c) => [c, airlineName(c)] as [string, string]).sort((a, b) => a[1].localeCompare(b[1])), [ways])

  const matches = (w: Way) =>
    (cabin === 'any' || w.cabin === cabin) &&
    filters.methods.includes(w.method) &&
    w.stops <= filters.maxStops &&
    (!filters.programs.length || (w.award ? filters.programs.includes(w.award.program) : false)) &&
    (!filters.airlines.length || w.carriers.some((c) => filters.airlines.includes(c))) &&
    (!filters.maxHours || w.duration_minutes <= filters.maxHours * 60) &&
    (!filters.maxAgeDays || !w.award || (w.award.data_age_hours >= 0 && w.award.data_age_hours <= filters.maxAgeDays * 24))

  const filtered = useMemo(() => ways.filter(matches), [ways, cabin, filters]) // eslint-disable-line react-hooks/exhaustive-deps
  const onDay = useMemo(() => filtered.filter((w) => w.departs_at.startsWith(day)), [filtered, day])
  const byBest = useMemo(() => [...onDay].sort((a, b) => a.score - b.score), [onDay])
  const byCheap = useMemo(() => [...onDay].sort((a, b) => a.estUsd - b.estUsd || a.duration_minutes - b.duration_minutes), [onDay])
  const list = tab === 'best' ? byBest : byCheap
  const top = tab === 'best' ? list.slice(0, 4) : []
  const rest = list.slice(top.length, top.length + shown)
  const lowestCash = Math.min(...onDay.filter((w) => w.cash).map((w) => w.estUsd))
  const finds = useMemo(() => buildFinds(ways, day, cabin, cash), [ways, day, cabin, cash])

  const dayBest = (d: string) => {
    const list = filtered.filter((w) => w.departs_at.startsWith(d))
    if (!list.length) return null
    return list.reduce((b, w) => (w.estUsd < b.estUsd ? w : b))
  }

  const goFind = (f: Find) => {
    if (f.cabin) setCabin(f.cabin)
    if (f.day) setDay(f.day)
    setFilters({ ...filters, methods: DEFAULT_FILTERS.methods, programs: [], airlines: [], maxStops: 9, maxHours: 0, maxAgeDays: 0 })
    setTab('cheapest'); setShown(200)
    if (f.wayId) {
      setOpenId(f.wayId)
      setTimeout(() => document.getElementById(`way-${f.wayId}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }), 80)
    }
  }

  const label = (w: Way | undefined) => (!w ? '–' : w.award ? `${miles(w.award.miles)} mi` : usd(w.estUsd))
  const tabBtn = (t: SortTab, title: string, w: Way | undefined) => (
    <button onClick={() => { setTab(t); setShown(PAGE) }}
      className={`flex-1 border-b-[3px] px-4 py-3 text-center ${tab === t ? 'border-brand bg-brand-soft/60 text-brand' : 'border-transparent hover:bg-hover'}`}>
      <span className="font-medium">{title}</span>
      {w && <span className="block text-sm text-sub sm:ml-2 sm:inline">from {label(w)}</span>}
    </button>
  )
  const rowProps = (w: Way) => ({ w, places, open: openId === w.id, onToggle: () => setOpenId(openId === w.id ? null : w.id), lowest: !!w.cash && w.estUsd === lowestCash })

  return (
    <div className="mx-auto max-w-[1024px] px-4 pt-4 pb-16">
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xl">
          <svg width="24" height="24" viewBox="0 0 24 24" className="text-brand" fill="currentColor" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" /></svg>
          <span className="font-medium">Waypoint</span>
        </div>
        {awards?.rate_limit_remaining != null && <span className="text-xs text-sub">{awards.rate_limit_remaining} award searches left today</span>}
      </header>

      <SearchCard initial={initial ?? { origin: 'DXB', destination: 'GVA', date: '2026-11-20', flex: 1 }} cabin={cabin} onCabin={setCabin} busy={busy} onSearch={setSearch} />

      {search && (
        <main className="mt-12 space-y-5">
          <Filters f={filters} set={(f) => { setFilters(f); setShown(PAGE) }} programs={programs} airlines={airlines} hasCash={!!cash} />

          {error && <p className="rounded-lg border border-bad/40 p-4 text-bad">{error}</p>}
          {cashNote && <p className="rounded-lg border border-line p-3 text-sm text-sub">Cash fares are not in this list: {cashNote} The list shows awards only.</p>}
          {busy && !ways.length && <p className="py-10 text-center text-sub">Searching cash fares and award seats in all cabins…</p>}

          {finds.length > 0 && (
            <section aria-label="Finds">
              <h2 className="mb-2 text-sm font-medium text-sub">Found for you</h2>
              <div className="-mx-4 flex gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-2 sm:overflow-visible sm:px-0 lg:grid-cols-4">
                {finds.slice(0, 4).map((f) => (
                  <button key={f.key} onClick={() => goFind(f)}
                    className="w-60 shrink-0 rounded-lg border border-line p-3 text-left hover:bg-hover sm:w-auto">
                    <div className="text-xs text-sub">{f.title}</div>
                    <div className={`text-lg font-medium tabular-nums ${FIND_TONE[f.tone]}`}>{f.headline}</div>
                    <div className="line-clamp-2 text-xs text-sub">{f.detail}</div>
                  </button>
                ))}
              </div>
            </section>
          )}

          {ways.length > 0 && (
            <>
              {dates.length > 1 && (
                <div className="grid grid-flow-col auto-cols-fr overflow-hidden rounded-lg border border-line">
                  {dates.map((d) => {
                    const b = dayBest(d)
                    return (
                      <button key={d} onClick={() => { setDay(d); setShown(PAGE); setOpenId(null) }}
                        className={`border-r border-line px-1 py-2 text-center last:border-r-0 ${d === day ? 'bg-brand-soft text-brand' : 'hover:bg-hover'}`}>
                        <div className="text-xs text-sub">{dayLabel(d)}</div>
                        <div className={`text-sm font-medium tabular-nums ${b?.award ? 'text-award' : ''}`}>{label(b ?? undefined)}</div>
                      </button>
                    )
                  })}
                </div>
              )}

              <div className="flex overflow-hidden rounded-lg border border-line">
                {tabBtn('best', 'Best', byBest[0])}
                <span className="w-px bg-line" />
                {tabBtn('cheapest', 'Cheapest', byCheap[0])}
              </div>

              {list.length === 0 && <p className="py-10 text-center text-sub">No options on {dayLabel(day)} with these filters.</p>}

              {top.length > 0 && (
                <section>
                  <h2 className="text-xl">Top ways to get there</h2>
                  <p className="mb-3 text-xs text-sub">
                    Ranked on cost, time and stops. Cash fares and awards are in one list{cabin !== 'any' && ` · ${CABIN_LABEL[cabin]}`}. Miles count as {filters.centsPerMile}¢ each.
                  </p>
                  <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">{top.map((w) => <WayRow key={w.id} {...rowProps(w)} />)}</ul>
                </section>
              )}

              {rest.length > 0 && (
                <section>
                  <h2 className="mb-3 text-xl">{tab === 'best' ? 'Other options' : 'All options, lowest cost first'}</h2>
                  <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">{rest.map((w) => <WayRow key={w.id} {...rowProps(w)} />)}</ul>
                  {list.length > top.length + shown && (
                    <button className="mt-3 w-full rounded-lg border border-line py-3 text-sm font-medium text-brand hover:bg-hover" onClick={() => setShown(shown + 30)}>
                      View {Math.min(30, list.length - top.length - shown)} more of {list.length - top.length - shown}
                    </button>
                  )}
                </section>
              )}

              {awards && (
                <p className="text-xs text-sub">
                  {ways.length} options from {awards.api_calls} award searches{cash ? ' and 4 cash searches' : ''}. Joined awards checked through {awards.hubs.join(', ')}.
                  Award seats come from the Seats.aero cache and can be gone. Award taxes in dollars are approximate.
                </p>
              )}
            </>
          )}
        </main>
      )}
    </div>
  )
}
