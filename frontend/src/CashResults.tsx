import { useEffect, useState } from 'react'
import { CABIN_LABEL, dayOffset, duration, money, time } from './format'
import type { Cabin, CashSearchResult, SearchParams } from './types'

const CABINS: Cabin[] = ['economy', 'premium', 'business', 'first']

export function CashResults({ search }: { search: SearchParams }) {
  const [cabin, setCabin] = useState<Cabin>('business')
  const [data, setData] = useState<CashSearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const ctl = new AbortController()
    setBusy(true)
    setError(null)
    setData(null)
    const q = new URLSearchParams({ origin: search.origin, destination: search.destination, date: search.date, cabin, currency: 'USD' })
    fetch(`/api/cash?${q}`, { signal: ctl.signal })
      .then(async (r) => {
        const body = await r.json()
        if (!r.ok) throw new Error(body.detail ?? r.statusText)
        setData(body)
      })
      .catch((e) => e.name !== 'AbortError' && setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
    return () => ctl.abort()
  }, [search, cabin])

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {CABINS.map((c) => (
          <button key={c} onClick={() => setCabin(c)}
            className={`rounded-full border px-3 py-1.5 text-sm ${
              c === cabin ? 'border-sky-600 bg-sky-50 text-sky-800 dark:border-sky-400 dark:bg-sky-950 dark:text-sky-200' : 'border-slate-300 dark:border-slate-700'
            }`}>
            {CABIN_LABEL[c]}
          </button>
        ))}
      </div>

      {busy && <p className="text-slate-500">Loading cash fares…</p>}
      {error && <p className="rounded-lg bg-amber-50 p-4 text-amber-900 dark:bg-amber-950 dark:text-amber-200">{error}</p>}

      {data && (
        <>
          {data.lowest_price !== null && (
            <p className="text-sm text-slate-600 dark:text-slate-400">
              Lowest {money(data.lowest_price, data.currency)}
              {data.price_level && <> · prices are <strong>{data.price_level}</strong></>}
              {data.typical_range && <> · usual range {money(data.typical_range[0], data.currency)}–{money(data.typical_range[1], data.currency)}</>}
            </p>
          )}
          <ul className="divide-y divide-slate-200 overflow-hidden rounded-xl bg-white ring-1 ring-slate-200 dark:divide-slate-800 dark:bg-slate-900 dark:ring-slate-800">
            {data.itineraries.map((it, i) => {
              const plus = dayOffset(it.departs_at, it.arrives_at)
              return (
                <li key={i} className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 px-4 py-3 sm:grid-cols-[9rem_8rem_1fr_7rem] sm:items-center">
                  <div>
                    <div className="font-semibold tabular-nums">
                      {time(it.departs_at)} – {time(it.arrives_at)}
                      {plus > 0 && <sup className="ml-0.5 text-xs text-rose-600">+{plus}</sup>}
                    </div>
                    <div className="text-xs text-slate-500">{it.airlines.join(', ')}</div>
                  </div>
                  <div className="order-3 text-sm tabular-nums sm:order-none">{duration(it.duration_minutes)}</div>
                  <div className="order-4 text-sm sm:order-none">
                    {it.stops === 0 ? 'Nonstop' : `${it.stops} stop${it.stops > 1 ? 's' : ''}`}
                    {it.via.length > 0 && <span className="text-slate-500"> · {it.via.join(', ')}</span>}
                    <div className="text-xs text-slate-500">{it.segments.map((s) => s.flight_number).join(' · ')}</div>
                  </div>
                  <div className="text-right font-semibold tabular-nums">{it.price !== null ? money(it.price, it.currency) : '—'}</div>
                </li>
              )
            })}
          </ul>
        </>
      )}
    </section>
  )
}
