import { useMemo, useState } from 'react'
import { age, CABIN_LABEL, dayLabel, dayOffset, duration, miles, money, time } from './format'
import type { AwardOption, AwardSearchResult, Cabin } from './types'

const CABINS: Cabin[] = ['economy', 'premium', 'business', 'first']
type Sort = 'miles' | 'duration' | 'departure'

const chip = (on: boolean) =>
  `rounded-full border px-3 py-1.5 text-sm transition ${
    on
      ? 'border-sky-600 bg-sky-50 text-sky-800 dark:border-sky-400 dark:bg-sky-950 dark:text-sky-200'
      : 'border-slate-300 text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-800'
  }`

export function AwardResults({ result }: { result: AwardSearchResult }) {
  const [cabin, setCabin] = useState<Cabin>('business')
  const [day, setDay] = useState<string>(result.dates[Math.floor(result.dates.length / 2)])
  const [program, setProgram] = useState<string>('all')
  const [maxStops, setMaxStops] = useState<number>(9)
  const [joined, setJoined] = useState(true)
  const [sort, setSort] = useState<Sort>('miles')

  const inCabin = useMemo(() => result.options.filter((o) => o.cabin === cabin), [result, cabin])
  const programs = useMemo(
    () => [...new Map(result.options.map((o) => [o.program, o.program_name])).entries()].sort((a, b) => a[1].localeCompare(b[1])),
    [result],
  )

  const cheapestByDay = useMemo(() => {
    const m: Record<string, number> = {}
    for (const o of inCabin) {
      const d = o.departs_at.slice(0, 10)
      if (m[d] === undefined || o.miles < m[d]) m[d] = o.miles
    }
    return m
  }, [inCabin])

  const rows = useMemo(() => {
    const list = inCabin.filter(
      (o) =>
        o.departs_at.startsWith(day) &&
        (program === 'all' || o.program === program) &&
        o.stops <= maxStops &&
        (joined || o.kind === 'direct'),
    )
    const key: Record<Sort, (o: AwardOption) => number | string> = {
      miles: (o) => o.miles * 1e4 + o.duration_minutes,
      duration: (o) => o.duration_minutes,
      departure: (o) => o.departs_at,
    }
    return list.sort((a, b) => (key[sort](a) < key[sort](b) ? -1 : key[sort](a) > key[sort](b) ? 1 : 0))
  }, [inCabin, day, program, maxStops, joined, sort])

  const cabinCounts = Object.fromEntries(CABINS.map((c) => [c, result.options.filter((o) => o.cabin === c && o.departs_at.startsWith(day)).length]))

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {CABINS.map((c) => (
          <button key={c} className={chip(c === cabin)} onClick={() => setCabin(c)}>
            {CABIN_LABEL[c]} <span className="text-slate-400">{cabinCounts[c]}</span>
          </button>
        ))}
      </div>

      <div className="grid grid-flow-col auto-cols-fr overflow-hidden rounded-xl ring-1 ring-slate-200 dark:ring-slate-800">
        {result.dates.map((d) => (
          <button key={d} onClick={() => setDay(d)}
            className={`border-r border-slate-200 px-2 py-2.5 text-center last:border-r-0 dark:border-slate-800 ${
              d === day ? 'bg-sky-600 text-white' : 'bg-white hover:bg-slate-50 dark:bg-slate-900 dark:hover:bg-slate-800'
            }`}>
            <div className="text-xs opacity-80">{dayLabel(d)}</div>
            <div className="font-semibold tabular-nums">{cheapestByDay[d] !== undefined ? miles(cheapestByDay[d]) : '–'}</div>
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <select className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900"
          value={program} onChange={(e) => setProgram(e.target.value)} aria-label="Program">
          <option value="all">All programs</option>
          {programs.map(([id, name]) => <option key={id} value={id}>{name}</option>)}
        </select>
        <select className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900"
          value={maxStops} onChange={(e) => setMaxStops(Number(e.target.value))} aria-label="Stops">
          <option value={9}>Any stops</option>
          <option value={0}>Nonstop</option>
          <option value={1}>1 stop or fewer</option>
          <option value={2}>2 stops or fewer</option>
        </select>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={joined} onChange={(e) => setJoined(e.target.checked)} />
          Include joined legs
        </label>
        <span className="ml-auto flex items-center gap-2">
          Sort
          <select className="rounded-lg border border-slate-300 bg-white px-2 py-1.5 dark:border-slate-700 dark:bg-slate-900"
            value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
            <option value="miles">Fewest miles</option>
            <option value="duration">Shortest</option>
            <option value="departure">Departure time</option>
          </select>
        </span>
      </div>

      <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl bg-white ring-1 ring-slate-200 dark:divide-slate-800 dark:bg-slate-900 dark:ring-slate-800">
        {rows.length === 0 && (
          <li className="p-6 text-center text-slate-500">No {CABIN_LABEL[cabin].toLowerCase()} award seats on {dayLabel(day)} with these filters.</li>
        )}
        {rows.map((o) => <AwardRow key={o.id} o={o} />)}
      </ul>
    </section>
  )
}

const toneClass = {
  fresh: 'text-emerald-700 dark:text-emerald-400',
  aging: 'text-amber-700 dark:text-amber-400',
  stale: 'text-rose-700 dark:text-rose-400',
}

function AwardRow({ o }: { o: AwardOption }) {
  const [open, setOpen] = useState(false)
  const a = age(o.data_age_hours)
  const plusDays = dayOffset(o.departs_at, o.arrives_at)

  return (
    <li>
      <button className="grid w-full grid-cols-[1fr_auto] gap-x-4 gap-y-1 px-4 py-3 text-left hover:bg-slate-50 sm:grid-cols-[9rem_8rem_1fr_9rem] sm:items-center dark:hover:bg-slate-800/60"
        onClick={() => setOpen(!open)} aria-expanded={open}>
        <div>
          <div className="font-semibold tabular-nums">
            {time(o.departs_at)} – {time(o.arrives_at)}
            {plusDays > 0 && <sup className="ml-0.5 text-xs text-rose-600">+{plusDays}</sup>}
          </div>
          <div className="text-xs text-slate-500">{o.carriers.join(', ')}</div>
        </div>
        <div className="order-3 sm:order-none">
          <div className="text-sm tabular-nums">{duration(o.duration_minutes)}</div>
          <div className="text-xs text-slate-500">{o.origin}–{o.destination}</div>
        </div>
        <div className="order-4 sm:order-none">
          <div className="text-sm">
            {o.stops === 0 ? 'Nonstop' : `${o.stops} stop${o.stops > 1 ? 's' : ''}`}
            {o.via.length > 0 && <span className="text-slate-500"> · {o.via.join(', ')}</span>}
          </div>
          <div className="flex flex-wrap items-center gap-x-2 text-xs text-slate-500">
            <span>{o.program_name}</span>
            {o.kind === 'joined' && (
              <span className="rounded bg-violet-100 px-1.5 py-0.5 text-violet-800 dark:bg-violet-950 dark:text-violet-300" title={o.note ?? ''}>
                joined
              </span>
            )}
            <span className={toneClass[a.tone]}>{a.label}</span>
          </div>
        </div>
        <div className="text-right">
          <div className="font-semibold tabular-nums">{o.miles.toLocaleString('en-US')} mi</div>
          <div className="text-xs text-slate-500 tabular-nums">
            + {money(o.taxes, o.taxes_currency)}
            {o.seats ? ` · ${o.seats} seat${o.seats > 1 ? 's' : ''}` : ''}
          </div>
        </div>
      </button>

      {open && (
        <div className="space-y-3 bg-slate-50 px-4 py-3 text-sm dark:bg-slate-950/50">
          {o.legs.map((l) => (
            <div key={l.availability_id + l.flight_numbers.join()} className="grid gap-1 sm:grid-cols-[9rem_1fr_auto]">
              <div className="tabular-nums">
                {l.departs_at.slice(5, 16).replace('T', ' ')} → {l.arrives_at.slice(11, 16)}
              </div>
              <div>
                <span className="font-medium">{l.flight_numbers.join(' · ')}</span>{' '}
                <span className="text-slate-500">
                  {[l.origin, ...l.connections, l.destination].join(' – ')} · {l.aircraft.join(', ')}
                  {l.fare_classes.length > 0 && ` · class ${[...new Set(l.fare_classes)].join('/')}`}
                </span>
              </div>
              {o.legs.length > 1 && (
                <div className="text-slate-500 tabular-nums">{l.miles.toLocaleString('en-US')} mi + {money(l.taxes, l.taxes_currency)}</div>
              )}
            </div>
          ))}
          {o.note && <p className="text-xs text-violet-800 dark:text-violet-300">{o.note}</p>}
          <div className="flex flex-wrap gap-3">
            <a className="rounded-full bg-sky-600 px-4 py-1.5 text-white hover:bg-sky-700" href={o.book_url} target="_blank" rel="noreferrer">
              Open {o.program_name}
            </a>
            <span className="self-center text-xs text-slate-500">Seat data from Seats.aero cache. Check on the program site before you transfer points.</span>
          </div>
        </div>
      )}
    </li>
  )
}
