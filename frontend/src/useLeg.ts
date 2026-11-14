import { useEffect, useState } from 'react'
import type { AwardSearchResult, Cabin, CashAll, TrickResult } from './types'

export interface LegData {
  awards: AwardSearchResult | null
  cash: CashAll | null
  tricks: TrickResult[]
  busy: boolean
  error: string | null
  cashNote: string | null
}

const EMPTY: LegData = { awards: null, cash: null, tricks: [], busy: false, error: null, cashNote: null }
// Fare tricks cost 2 to 3 cash searches for each cabin, so they run for these two only.
const TRICK_CABINS: Cabin[] = ['economy', 'business']

async function get(url: string, signal: AbortSignal) {
  const r = await fetch(url, { signal })
  const body = await r.json()
  if (!r.ok) throw new Error(typeof body.detail === 'string' ? body.detail : r.statusText)
  return body
}

/** All data for one direction of travel. One search fans out to every source. */
export function useLeg(origin: string | null, destination: string | null, date: string | null, flex: number, returnTrick: boolean): LegData {
  const [d, setD] = useState<LegData>(EMPTY)
  useEffect(() => {
    if (!origin || !destination || !date) { setD(EMPTY); return }
    const ctl = new AbortController()
    const q = new URLSearchParams({ origin, destination, date })
    const live = <T,>(f: (v: T) => void) => (v: T) => { if (!ctl.signal.aborted) f(v) }
    setD({ ...EMPTY, busy: true })
    const a = get(`/api/awards?${q}&flex=${flex}`, ctl.signal).then(live((awards: AwardSearchResult) => setD((s) => ({ ...s, awards }))))
      .catch(live((e: Error) => setD((s) => ({ ...s, error: e.message }))))
    const c = get(`/api/cash/all?${q}`, ctl.signal).then(live((cash: CashAll) => {
      setD((s) => ({ ...s, cash }))
      return Promise.allSettled(TRICK_CABINS.map((cabin) =>
        get(`/api/tricks?${q}&cabin=${cabin}&include_return=${returnTrick}`, ctl.signal).then(live((t: TrickResult) => setD((s) => ({ ...s, tricks: [...s.tricks, t] })))),
      ))
    })).catch(live((e: Error) => setD((s) => ({ ...s, cashNote: e.message }))))
    Promise.allSettled([a, c]).then(live(() => setD((s) => ({ ...s, busy: false }))))
    return () => ctl.abort()
  }, [origin, destination, date, flex, returnTrick])
  return d
}
