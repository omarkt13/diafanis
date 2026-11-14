import { useEffect, useState } from 'react'
import { airlineName, badgeColor, carrierOf } from './airlines'
import { dayOffset, duration, time } from './format'
import type { Leg, Places, Segment } from './types'

export function Logo({ codes }: { codes: string[] }) {
  const [failed, setFailed] = useState(false)
  const code = codes[0] ?? '?'
  if (codes.length === 1 && !failed) {
    return <img src={`https://www.gstatic.com/flights/airline_logos/70px/${code}.png`} alt="" width={35} height={35}
      className="h-9 w-9 object-contain" onError={() => setFailed(true)} />
  }
  return (
    <span className="flex h-9 w-9 items-center justify-center rounded-full text-[11px] font-semibold text-white" style={{ background: badgeColor(code) }}>
      {codes.length > 1 ? `${codes.length}×` : code}
    </span>
  )
}

export interface BookLink { label: string; link: string; primary: boolean }

/** Per-flight times and booking links for award legs (1 cached API call for each leg). */
export function useAwardSegments(legs: Leg[] | null, enabled: boolean): { segments: Segment[]; links: BookLink[] } {
  const [detail, setDetail] = useState<Record<number, { segments: Segment[]; links: BookLink[] }>>({})
  useEffect(() => {
    if (!legs || !enabled) return
    let live = true
    legs.forEach((l, i) => {
      const q = new URLSearchParams({ availability_id: l.availability_id, flights: l.flight_numbers.join(',') })
      fetch(`/api/awards/segments?${q}`).then((r) => (r.ok ? r.json() : null)).then((d) => {
        if (live && d?.segments?.length) setDetail((prev) => ({ ...prev, [i]: { segments: d.segments, links: d.booking_links } }))
      }).catch(() => {})
    })
    return () => { live = false }
  }, [legs, enabled])

  // Until the flight times load, show each award leg as one block.
  const segments = (legs ?? []).flatMap((l, i) =>
    detail[i]?.segments ?? [{
      flight_number: l.flight_numbers.join(' + '), origin: l.origin, destination: l.destination, departs_at: l.departs_at,
      arrives_at: l.arrives_at, duration_minutes: l.duration_minutes, aircraft: l.aircraft.join(', '),
      note: l.connections.length ? `via ${l.connections.join(', ')}` : null,
    }])
  return { segments, links: Object.values(detail).find((d) => d.links.length)?.links ?? [] }
}

export function Timeline({ segs, places }: { segs: Segment[]; places: Places }) {
  const place = (c: string) => (places[c] ? `${places[c].name} (${c})` : c)
  return (
    <div>
      {segs.map((s, i) => {
        const next = segs[i + 1]
        const lay = next ? Math.round((Date.parse(next.departs_at) - Date.parse(s.arrives_at)) / 60000) : 0
        const ground = /\b(bus|train|rail)\b|surface/i.test(s.aircraft ?? '')
        return (
          <div key={i}>
            <div className="grid grid-cols-[1.25rem_1fr] gap-x-3">
              <div className="flex flex-col items-center pt-1.5">
                <span className="h-3 w-3 rounded-full border-2 border-sub" />
                <span className="my-1 w-0 flex-1 border-l-4 border-dotted border-line" />
                <span className="h-3 w-3 rounded-full border-2 border-sub" />
              </div>
              <div className="space-y-2 pb-1">
                <p><span className="font-medium tabular-nums">{time(s.departs_at)}</span> · {place(s.origin)}</p>
                <p className="text-sm text-sub">{s.duration_minutes > 0 && `Travel time: ${duration(s.duration_minutes)}`}{dayOffset(s.departs_at, s.arrives_at) > 0 && ' · arrives next day'}</p>
                <p><span className="font-medium tabular-nums">{time(s.arrives_at)}</span> · {place(s.destination)}</p>
                <p className="text-xs text-sub">
                  {airlineName(carrierOf(s.flight_number))} · {s.flight_number}{s.aircraft && ` · ${s.aircraft}`}{s.note && ` · ${s.note}`}
                  {ground && <span className="ml-2 rounded bg-warn/15 px-1.5 py-0.5 font-medium text-warn">Ground transport, not a flight</span>}
                </p>
              </div>
            </div>
            {next && (
              <div className="my-3 ml-8 border-y border-line py-3 text-sm">
                {lay > 0 ? `${duration(lay)} layover` : 'Connection'} · {places[s.destination]?.city ?? s.destination} ({s.destination})
                {lay >= 8 * 60 && <span className="ml-2 text-warn">Long layover</span>}
                {s.destination !== next.origin && <span className="ml-2 text-bad">Change of airport</span>}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
