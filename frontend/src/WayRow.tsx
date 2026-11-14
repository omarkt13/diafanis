import { useEffect, useState } from 'react'
import { airlineName, badgeColor, carrierOf } from './airlines'
import { age, CABIN_LABEL, dayLabel, dayOffset, duration, money, time, usd } from './format'
import type { Places, Segment, Way } from './types'

function Logo({ codes }: { codes: string[] }) {
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

const TONE = { fresh: 'text-good', aging: 'text-warn', stale: 'text-bad' }
const METHOD = {
  cash: { label: 'Cash fare', cls: 'bg-brand-soft text-brand' },
  award: { label: 'Award', cls: 'bg-award-soft text-award' },
  joined: { label: 'Joined award', cls: 'bg-award-soft text-award' },
}

interface LegDetail { segments: Segment[]; links: { label: string; link: string; primary: boolean }[] }

function Timeline({ segs, places }: { segs: Segment[]; places: Places }) {
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
                <p className="text-sm text-sub">{s.duration_minutes > 0 && `Travel time: ${duration(s.duration_minutes)}`}{dayOffset(s.departs_at, s.arrives_at) > 0 && ' · overnight'}</p>
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

function AwardDetail({ w, places }: { w: Way; places: Places }) {
  const a = w.award!
  const [detail, setDetail] = useState<(LegDetail | null)[]>(a.legs.map(() => null))

  useEffect(() => {
    let live = true
    a.legs.forEach((l, i) => {
      const q = new URLSearchParams({ availability_id: l.availability_id, flights: l.flight_numbers.join(',') })
      fetch(`/api/awards/segments?${q}`).then((r) => (r.ok ? r.json() : null)).then((d) => {
        if (live && d?.segments?.length) setDetail((prev) => prev.map((x, j) => (j === i ? { segments: d.segments, links: d.booking_links } : x)))
      }).catch(() => {})
    })
    return () => { live = false }
  }, [a])

  // Until per-flight times load, show each award leg as one block.
  const segs: Segment[] = a.legs.flatMap((l, i) =>
    detail[i]?.segments ?? [{
      flight_number: l.flight_numbers.join(' + '), origin: l.origin, destination: l.destination, departs_at: l.departs_at,
      arrives_at: l.arrives_at, duration_minutes: l.duration_minutes, aircraft: l.aircraft.join(', '),
      note: l.connections.length ? `via ${l.connections.join(', ')}` : null,
    }])
  const links = detail.find((d) => d?.links.length)?.links ?? []
  const ag = age(a.data_age_hours)

  return (
    <div className="grid gap-6 md:grid-cols-[1fr_18rem]">
      <Timeline segs={segs} places={places} />
      <div className="space-y-3 text-sm">
        <div className="rounded-lg border border-line p-3">
          <p className="font-medium">{a.program_name}</p>
          <p className="tabular-nums">{a.miles.toLocaleString('en-US')} miles + {a.taxes_currency && a.taxes_currency !== 'mixed' ? money(a.taxes, a.taxes_currency) : `≈ ${usd(a.taxes_usd)}`}</p>
          {a.legs.length > 1 && a.legs.map((l, i) => (
            <p key={i} className="text-xs text-sub tabular-nums">{l.origin}–{l.destination}: {l.miles.toLocaleString('en-US')} mi + {money(l.taxes, l.taxes_currency ?? 'USD')}</p>
          ))}
          {w.cpp !== null && <p className="mt-1 text-good">Worth {w.cpp.toFixed(1)}¢ per mile against the {usd(w.cashRef!)} cash fare</p>}
          <p className={`mt-1 text-xs ${TONE[ag.tone]}`}>Seats {ag.label}{a.seats ? ` · ${a.seats} left` : ''}</p>
        </div>
        {a.note && <p className="rounded-lg bg-award-soft p-3 text-xs text-award">{a.note}</p>}
        <div className="flex flex-wrap gap-2">
          {(links.length ? links : [{ label: `Open ${a.program_name}`, link: a.book_url, primary: true }]).map((b) => (
            <a key={b.label} href={b.link} target="_blank" rel="noreferrer"
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${b.primary ? 'bg-brand text-page' : 'border border-line text-brand hover:bg-hover'}`}>{b.label}</a>
          ))}
        </div>
        <p className="text-xs text-sub">Check the seats on the program site before you transfer points.</p>
      </div>
    </div>
  )
}

export function WayRow({ w, places, open, onToggle, lowest }: { w: Way; places: Places; open: boolean; onToggle: () => void; lowest: boolean }) {
  const plus = dayOffset(w.departs_at, w.arrives_at)
  const m = METHOD[w.method]
  const a = w.award
  const ag = a ? age(a.data_age_hours) : null
  const names = w.carriers.map(airlineName)

  return (
    <li id={`way-${w.id}`} className={open ? 'bg-hover/40' : ''}>
      <button className="grid w-full grid-cols-[2.25rem_1fr_auto] items-center gap-x-4 gap-y-2 px-4 py-4 text-left hover:bg-hover/60 md:grid-cols-[2.25rem_1.5fr_1fr_1fr_1.2fr_auto_1.5rem] md:px-6"
        onClick={onToggle} aria-expanded={open}>
        <Logo codes={w.carriers} />
        <div className="min-w-0">
          <div className="text-base font-medium tabular-nums">
            {time(w.departs_at)} – {time(w.arrives_at)}{plus > 0 && <sup className="ml-0.5 text-[11px] font-normal">+{plus}</sup>}
          </div>
          <div className="truncate text-xs text-sub">{names.join(', ')}{w.ground && ' · includes ground transport'}</div>
        </div>
        <div className="col-start-2 md:col-start-auto">
          <div className="text-sm tabular-nums md:text-base">{duration(w.duration_minutes)}</div>
          <div className="text-xs text-sub">{a ? `${a.origin}–${a.destination}` : w.cash ? `${w.cash.segments[0].origin}–${w.cash.segments.at(-1)!.destination}` : ''}</div>
        </div>
        <div className="hidden md:block">
          <div className="text-base">{w.stops === 0 ? 'Nonstop' : `${w.stops} stop${w.stops > 1 ? 's' : ''}`}</div>
          <div className="truncate text-xs text-sub">{w.via.join(', ')}</div>
        </div>
        <div className="col-start-2 flex flex-wrap items-center gap-x-2 gap-y-1 md:col-start-auto md:block">
          <span className={`inline-block rounded px-1.5 py-0.5 text-xs font-medium ${m.cls}`}>{m.label}</span>
          <span className="text-xs text-sub md:hidden">{w.stops === 0 ? 'Nonstop' : `${w.stops} stop${w.stops > 1 ? 's' : ''} · ${w.via.join(', ')}`}</span>
          <div className="truncate text-xs text-sub md:mt-0.5">
            {a ? a.program_name : CABIN_LABEL[w.cabin]}
            {ag && <span className={`ml-1.5 ${TONE[ag.tone]}`}>· {ag.label.replace('checked ', '')}</span>}
          </div>
        </div>
        <div className="col-start-3 row-span-2 row-start-1 self-start text-right md:col-start-auto md:row-auto md:self-center">
          {a ? (
            <>
              <div className="text-base font-medium tabular-nums text-award">{a.miles.toLocaleString('en-US')} <span className="text-xs font-normal">mi</span></div>
              <div className="text-xs text-sub tabular-nums">+ {a.taxes_currency && a.taxes_currency !== 'mixed' ? money(a.taxes, a.taxes_currency) : `≈ ${usd(a.taxes_usd)}`}</div>
              {w.cpp !== null && <div className="text-xs font-medium text-good tabular-nums">{w.cpp.toFixed(1)}¢/mi</div>}
            </>
          ) : (
            <>
              <div className={`text-base font-medium tabular-nums ${lowest ? 'text-good' : ''}`}>{usd(w.estUsd)}</div>
              <div className="text-xs text-sub">{CABIN_LABEL[w.cabin]}</div>
            </>
          )}
        </div>
        <span className={`hidden text-sub transition md:block ${open ? 'rotate-180' : ''}`} aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m6 9 6 6 6-6" /></svg>
        </span>
      </button>

      {open && (
        <div className="border-t border-line px-4 py-5 md:px-6 md:pl-[4.75rem]">
          <p className="mb-4 text-sm text-sub">{dayLabel(w.departs_at, true)} · {CABIN_LABEL[w.cabin]}</p>
          {a ? <AwardDetail w={w} places={places} /> : (
            <div className="grid gap-6 md:grid-cols-[1fr_18rem]">
              <Timeline places={places} segs={w.cash!.segments.map((s) => ({ ...s, note: s.travel_class }))} />
              <div className="space-y-3 text-sm">
                <div className="rounded-lg border border-line p-3">
                  <p className="font-medium">Cash fare</p>
                  <p className="tabular-nums">{usd(w.estUsd)} one way</p>
                </div>
                <a className="inline-block rounded-full bg-brand px-4 py-1.5 font-medium text-page" target="_blank" rel="noreferrer"
                  href={`https://www.google.com/travel/flights?q=${encodeURIComponent(`one way flight ${w.cash!.segments[0].origin} to ${w.cash!.segments.at(-1)!.destination} on ${w.departs_at.slice(0, 10)} ${CABIN_LABEL[w.cabin]}`)}`}>
                  Open in Google Flights
                </a>
              </div>
            </div>
          )}
        </div>
      )}
    </li>
  )
}
