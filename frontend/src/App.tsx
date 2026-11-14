import { useEffect, useMemo, useState } from 'react'
import { airlineName } from './airlines'
import { DEFAULT_FILTERS, Filters, type FilterState } from './Filters'
import { CABIN_LABEL, dayLabel, miles, time, usd } from './format'
import { RouteRow } from './RouteRow'
import { awardUsd, buildRoutes, buildTricks, filterRoutes, rankLowest, rankValue, VALUE } from './routes'
import { SearchCard } from './SearchCard'
import { TrickRow } from './TrickRow'
import type { AwardOption, Cabin, CashAll, Offer, Places, Route, SearchParams, TransferData, TrickItem, Wallet } from './types'
import { useLeg } from './useLeg'
import { WalletDialog } from './WalletDialog'

type View = 'lowest' | 'value' | 'tricks'
type Dir = 'out' | 'back'
const PAGE = 15

function fromUrl(): SearchParams | null {
  const q = new URLSearchParams(window.location.search)
  const origin = q.get('from'), destination = q.get('to'), date = q.get('date')
  if (!origin || !destination || !date) return null
  return { origin, destination, date, flex: Number(q.get('flex') ?? 1), returnDate: q.get('ret') }
}
function stored<T>(key: string, fallback: T): T {
  try { const v = localStorage.getItem(key); return v ? (JSON.parse(v) as T) : fallback } catch { return fallback }
}
function store(key: string, v: unknown) { try { localStorage.setItem(key, JSON.stringify(v)) } catch { /* private mode */ } }

interface Best { usd: number; text: string; award: boolean }

/** Cheapest way to fly one direction in one cabin: cash only, and any payment. */
function bestOf(routes: Route[], joined: AwardOption[], day: string, cabin: Cabin, cpm: number): { cash: Best | null; any: Best | null } {
  let cash: Best | null = null, any: Best | null = null
  const say = (r: Route, o: Offer) => `${r.carriers.map(airlineName).join(' + ')} ${time(r.departs_at)}, ${o.kind === 'cash' ? `${usd(o.usd)} cash` : `${miles(o.award!.miles)} ${o.award!.program_name} miles + ${usd(o.award!.taxes_usd)}`}`
  for (const r of routes) {
    if (r.day !== day) continue
    for (const o of r.offers) {
      if (o.cabin !== cabin) continue
      const b = { usd: o.usd, text: say(r, o), award: o.kind === 'award' }
      if (o.kind === 'cash' && (!cash || o.usd < cash.usd)) cash = b
      if (!any || o.usd < any.usd) any = b
    }
  }
  for (const j of joined) {
    const v = awardUsd(j, cpm)
    if (j.cabin === cabin && j.departs_at.startsWith(day) && (!any || v < any.usd)) {
      any = { usd: v, award: true, text: `${j.carriers.map(airlineName).join(' + ')} ${time(j.departs_at)}, ${miles(j.miles)} ${j.program_name} miles + ${usd(j.taxes_usd)} (joined legs)` }
    }
  }
  return { cash, any }
}

export default function App() {
  const initial = useMemo(fromUrl, [])
  const [search, setSearch] = useState<SearchParams | null>(initial)
  const [dir, setDir] = useState<Dir>('out')
  const [view, setView] = useState<View>('lowest')
  const [days, setDays] = useState<Record<Dir, string>>({ out: initial?.date ?? '', back: initial?.returnDate ?? '' })
  const [filters, setFilters] = useState<FilterState>(() => ({ ...DEFAULT_FILTERS, centsPerMile: stored('cpm', DEFAULT_FILTERS.centsPerMile) }))
  const [openId, setOpenId] = useState<string | null>(null)
  const [shown, setShown] = useState(PAGE)
  const [places, setPlaces] = useState<Places>({})
  const [wallet, setWallet] = useState<Wallet>(() => stored('wallet', { programs: {}, currencies: {} }))
  const [transfers, setTransfers] = useState<TransferData | null>(null)
  const [walletOpen, setWalletOpen] = useState(false)
  const [rtCash, setRtCash] = useState<CashAll | null>(null)

  const rt = !!search?.returnDate
  const out = useLeg(search?.origin ?? null, search?.destination ?? null, search?.date ?? null, search?.flex ?? 1, !rt)
  const back = useLeg(rt ? search!.destination : null, rt ? search!.origin : null, search?.returnDate ?? null, search?.flex ?? 1, false)
  const cpm = filters.centsPerMile

  useEffect(() => store('cpm', cpm), [cpm])
  useEffect(() => store('wallet', wallet), [wallet])
  useEffect(() => { fetch('/api/transfers').then((r) => r.json()).then(setTransfers).catch(() => {}) }, [])

  useEffect(() => {
    if (!search) return
    const q = new URLSearchParams({ from: search.origin, to: search.destination, date: search.date, flex: String(search.flex) })
    if (search.returnDate) q.set('ret', search.returnDate)
    window.history.replaceState(null, '', `?${q}`)
    setDays({ out: search.date, back: search.returnDate ?? '' }); setDir('out'); setOpenId(null); setShown(PAGE); setRtCash(null)
    if (!search.returnDate) return
    const ctl = new AbortController()
    const api = new URLSearchParams({ origin: search.origin, destination: search.destination, date: search.date, return_date: search.returnDate })
    fetch(`/api/cash/roundtrip?${api}`, { signal: ctl.signal }).then((r) => (r.ok ? r.json() : null)).then((d) => d && setRtCash(d)).catch(() => {})
    return () => ctl.abort()
  }, [search])

  const builtOut = useMemo(() => buildRoutes(out.awards, out.cash, cpm, wallet, transfers), [out.awards, out.cash, cpm, wallet, transfers])
  const builtBack = useMemo(() => buildRoutes(back.awards, back.cash, cpm, wallet, transfers), [back.awards, back.cash, cpm, wallet, transfers])
  const leg = dir === 'out' ? out : back
  const built = dir === 'out' ? builtOut : builtBack
  const day = days[dir]
  const dates = leg.awards?.dates ?? (day ? [day] : [])

  useEffect(() => {
    const codes = new Set<string>()
    for (const b of [builtOut, builtBack]) {
      for (const r of b.routes) { [r.origin, r.destination, ...r.via].forEach((c) => codes.add(c)) }
      for (const j of b.joined) j.legs.forEach((l) => [l.origin, l.destination, ...l.connections].forEach((c) => codes.add(c)))
    }
    for (const t of [...out.tricks, ...back.tricks]) t.tricks.forEach((x) => x.ticketed_to && codes.add(x.ticketed_to))
    const missing = [...codes].filter((c) => !places[c])
    if (!missing.length) return
    fetch(`/api/airports/lookup?codes=${missing.join(',')}`).then((r) => r.json()).then((d) => setPlaces((p) => ({ ...p, ...d }))).catch(() => {})
  }, [builtOut, builtBack, out.tricks, back.tricks]) // eslint-disable-line react-hooks/exhaustive-deps

  const programs = useMemo(() => {
    const m = new Map<string, string>()
    for (const r of built.routes) for (const o of r.offers) if (o.award) m.set(o.award.program, o.award.program_name)
    for (const j of built.joined) m.set(j.program, j.program_name)
    return [...m.entries()].sort((a, b) => a[1].localeCompare(b[1]))
  }, [built])
  const airlines = useMemo(() => [...new Set([...built.routes.flatMap((r) => r.carriers), ...built.joined.flatMap((j) => j.carriers)])]
    .map((c) => [c, airlineName(c)] as [string, string]).sort((a, b) => a[1].localeCompare(b[1])), [built])

  const filtered = useMemo(() => filterRoutes(built.routes, filters, day), [built, filters, day])
  const lowest = useMemo(() => rankLowest(filtered), [filtered])
  const value = useMemo(() => rankValue(filtered), [filtered])

  // Round trip: compare one return ticket with two one-way tickets and with a mix of cash and miles.
  const pairs = useMemo(() => {
    if (!rt) return []
    return filters.cabins.map((cabin) => {
      const o = bestOf(builtOut.routes, builtOut.joined, days.out, cabin, cpm)
      const b = bestOf(builtBack.routes, builtBack.joined, days.back, cabin, cpm)
      const ticket = rtCash?.cabins[cabin]?.itineraries.reduce<number | null>((m, it) => (it.price != null && (m === null || it.price < m) ? it.price : m), null) ?? null
      const twoCash = o.cash && b.cash ? o.cash.usd + b.cash.usd : null
      const mix = o.any && b.any && (o.any.award || b.any.award) ? o.any.usd + b.any.usd : null
      return { cabin, ticket, twoCash, mix, o, b }
    }).filter((p) => p.ticket !== null || p.twoCash !== null || p.mix !== null)
  }, [rt, filters.cabins, builtOut, builtBack, days, cpm, rtCash])

  const splitItems = useMemo(() => {
    const items: TrickItem[] = []
    for (const p of pairs) {
      if (p.twoCash !== null && p.ticket !== null && p.twoCash < p.ticket * 0.97) {
        items.push({ id: `split|cash|${p.cabin}`, kind: 'split', cabin: p.cabin, usd: p.twoCash, compareUsd: p.ticket, title: 'Two one-way tickets in place of one return ticket',
          sub: `Round trip, ${CABIN_LABEL[p.cabin].toLowerCase()}`, parts: [`Out: ${p.o.cash!.text}`, `Back: ${p.b.cash!.text}`] })
      }
      const ref = Math.min(p.ticket ?? Infinity, p.twoCash ?? Infinity)
      if (p.mix !== null && p.mix < ref * 0.97) {
        items.push({ id: `split|mix|${p.cabin}`, kind: 'split', cabin: p.cabin, usd: p.mix, compareUsd: Number.isFinite(ref) ? ref : null, title: 'Mix cash and miles for the two directions',
          sub: `Round trip, ${CABIN_LABEL[p.cabin].toLowerCase()} · miles count as ${cpm}¢ each`, parts: [`Out: ${p.o.any!.text}`, `Back: ${p.b.any!.text}`] })
      }
    }
    return items
  }, [pairs, cpm])

  const tricks = useMemo(
    () => buildTricks(built.routes, built.joined, leg.tricks, built.cashLowest, filters, day, cpm, wallet, transfers, splitItems),
    [built, leg.tricks, filters, day, cpm, wallet, transfers, splitItems],
  )

  const priceOf = (o: Offer | undefined) => (!o ? '' : o.kind === 'cash' ? usd(o.usd) : `${miles(o.award!.miles)} mi`)
  const dayBest = (d: string) => priceOf(rankLowest(filterRoutes(built.routes, filters, d))[0]?.pick) || '–'
  const reset = () => { setShown(PAGE); setOpenId(null) }
  const tab = (v: View, title: string, sub: string) => (
    <button onClick={() => { setView(v); reset() }}
      className={`flex-1 border-b-[3px] px-2 py-3 text-center ${view === v ? 'border-brand bg-brand-soft/60 text-brand' : 'border-transparent hover:bg-hover'}`}>
      <span className="block font-medium sm:inline">{title}</span>
      {sub && <span className="block text-xs text-sub sm:ml-2 sm:inline sm:text-sm">{sub}</span>}
    </button>
  )
  const busy = out.busy || back.busy
  const hasData = built.routes.length > 0 || built.joined.length > 0
  const list = view === 'lowest' ? lowest : value
  const total = view === 'tricks' ? tricks.length : list.length
  const searches = (out.awards?.api_calls ?? 0) + (back.awards?.api_calls ?? 0)
  const od = dir === 'out' ? [search?.origin, search?.destination] : [search?.destination, search?.origin]

  return (
    <div className="mx-auto max-w-[1080px] px-4 pt-4 pb-16">
      <header className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xl">
          <svg width="24" height="24" viewBox="0 0 24 24" className="text-brand" fill="currentColor" aria-hidden="true"><path d="M21 16v-2l-8-5V3.5a1.5 1.5 0 0 0-3 0V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5z" /></svg>
          <span className="font-medium">Waypoint</span>
        </div>
        <div className="flex items-center gap-3">
          {out.awards?.rate_limit_remaining != null && <span className="hidden text-xs text-sub sm:inline">{(back.awards ?? out.awards).rate_limit_remaining} award searches left today</span>}
          <button className="rounded-full border border-line px-4 py-1.5 text-sm font-medium text-brand hover:bg-hover" onClick={() => setWalletOpen(true)}>My points</button>
        </div>
      </header>
      {walletOpen && transfers && <WalletDialog wallet={wallet} transfers={transfers} onSave={setWallet} onClose={() => setWalletOpen(false)} />}

      <SearchCard initial={initial ?? { origin: 'DXB', destination: 'GVA', date: '2026-11-20', flex: 1, returnDate: null }} busy={busy} onSearch={setSearch} />

      {search && (
        <main className="mt-12 space-y-5">
          <Filters f={filters} set={(f) => { setFilters(f); reset() }} programs={programs} airlines={airlines} hasCash={!!leg.cash} />

          {leg.error && <p className="rounded-lg border border-bad/40 p-4 text-bad">{leg.error}</p>}
          {leg.cashNote && <p className="rounded-lg border border-line p-3 text-sm text-sub">Cash fares are not in this list: {leg.cashNote} The list shows awards only.</p>}
          {busy && !hasData && <p className="py-10 text-center text-sub">Searching cash fares, award seats and fare tricks in all cabins…</p>}

          {rt && (
            <div className="flex overflow-hidden rounded-full border border-line text-sm">
              {(['out', 'back'] as Dir[]).map((d) => (
                <button key={d} onClick={() => { setDir(d); reset() }} className={`flex-1 px-4 py-2 ${dir === d ? 'bg-brand text-page' : 'hover:bg-hover'}`}>
                  {d === 'out' ? `Outbound · ${search.origin}–${search.destination}` : `Return · ${search.destination}–${search.origin}`} · {dayLabel(days[d])}
                </button>
              ))}
            </div>
          )}

          {rt && pairs.length > 0 && (
            <section className="overflow-x-auto rounded-lg border border-line">
              <table className="w-full min-w-[30rem] text-sm">
                <thead className="text-left text-xs text-sub">
                  <tr><th className="px-3 py-2 font-medium">Round trip, total</th><th className="px-3 py-2 font-medium">One return ticket</th><th className="px-3 py-2 font-medium">Two one-way tickets</th><th className="px-3 py-2 font-medium">Mix of cash and miles</th></tr>
                </thead>
                <tbody>
                  {pairs.map((p) => {
                    const min = Math.min(p.ticket ?? Infinity, p.twoCash ?? Infinity, p.mix ?? Infinity)
                    const cell = (v: number | null, approx = false) => <td className={`px-3 py-2 tabular-nums ${v === min ? 'font-semibold text-good' : ''}`}>{v === null ? '–' : `${approx ? '≈ ' : ''}${usd(v)}`}</td>
                    return <tr key={p.cabin} className="border-t border-line"><td className="px-3 py-2">{CABIN_LABEL[p.cabin]}</td>{cell(p.ticket)}{cell(p.twoCash)}{cell(p.mix, true)}</tr>
                  })}
                </tbody>
              </table>
            </section>
          )}

          {hasData && (
            <>
              {dates.length > 1 && (
                <div className="grid grid-flow-col auto-cols-fr overflow-hidden rounded-lg border border-line">
                  {dates.map((d) => (
                    <button key={d} onClick={() => { setDays({ ...days, [dir]: d }); reset() }}
                      className={`border-r border-line px-1 py-2 text-center last:border-r-0 ${d === day ? 'bg-brand-soft text-brand' : 'hover:bg-hover'}`}>
                      <div className="text-xs text-sub">{dayLabel(d)}</div>
                      <div className="text-sm font-medium tabular-nums">{dayBest(d)}</div>
                    </button>
                  ))}
                </div>
              )}

              <div className="flex overflow-hidden rounded-lg border border-line">
                {tab('lowest', 'Lowest cost', lowest[0] ? `from ${priceOf(lowest[0].pick)}` : '')}
                <span className="w-px bg-line" />
                {tab('value', 'Best value', value[0] ? `${CABIN_LABEL[value[0].pick.cabin].split(' ')[0]} ${priceOf(value[0].pick)}` : '')}
                <span className="w-px bg-line" />
                {tab('tricks', 'Tricks', tricks[0] ? `${tricks.length} · from ${usd(tricks[0].usd)}` : 'none')}
              </div>

              <section>
                <h2 className="text-xl">
                  {view === 'lowest' ? 'Lowest cost' : view === 'value' ? 'Best value' : 'Tricks'}
                  <span className="ml-2 text-sm text-sub">{od[0]}–{od[1]} · {dayLabel(day)}</span>
                </h2>
                <p className="mb-3 text-xs text-sub">
                  {view === 'lowest' && `Each row is one set of flights with its fares in all cabins. Rows are in order of the lowest cost in dollars. Miles count as ${cpm}¢ each, plus award taxes.`}
                  {view === 'value' && `In order of cost for what you get: a business seat counts as ${VALUE.worth.business}× economy, premium ${VALUE.worth.premium}×, first ${VALUE.worth.first}×. Each stop adds $${VALUE.perStop} and each hour above the fastest route adds $${VALUE.perExtraHour}. Old award data ranks lower.`}
                  {view === 'tricks' && 'Other ways to buy the trip: return tickets, hidden-city tickets, joined award legs, a seat through the program of another airline, and split tickets. Always in order of cost.'}
                </p>

                {total === 0 && <p className="rounded-lg border border-line py-10 text-center text-sub">{view === 'tricks' ? (leg.cash ? 'No trick costs less than the normal fares on this date.' : 'No tricks found. Return-ticket and hidden-city fares need cash fares.') : `No options on ${dayLabel(day)} with these filters.`}</p>}

                {view !== 'tricks' && list.length > 0 && (
                  <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
                    {list.slice(0, shown).map((r) => <RouteRow key={r.route.key} r={r} places={places} view={view} open={openId === r.route.key} onToggle={() => setOpenId(openId === r.route.key ? null : r.route.key)} />)}
                  </ul>
                )}
                {view === 'tricks' && tricks.length > 0 && (
                  <ul className="divide-y divide-line overflow-hidden rounded-lg border border-line">
                    {tricks.slice(0, shown).map((t) => <TrickRow key={t.id} t={t} places={places} open={openId === t.id} onToggle={() => setOpenId(openId === t.id ? null : t.id)} />)}
                  </ul>
                )}
                {total > shown && (
                  <button className="mt-3 w-full rounded-lg border border-line py-3 text-sm font-medium text-brand hover:bg-hover" onClick={() => setShown(shown + 30)}>
                    View {Math.min(30, total - shown)} more of {total - shown}
                  </button>
                )}
              </section>

              <p className="text-xs text-sub">
                {built.routes.length} routes and {built.joined.length} joined awards from {searches} award searches{leg.cash ? ' and cash searches in 4 cabins' : ''}.
                Award seats come from the Seats.aero cache and can be gone. Award taxes in dollars are approximate. Cash fares and fare tricks are for the search date only.
              </p>
            </>
          )}
        </main>
      )}
    </div>
  )
}
