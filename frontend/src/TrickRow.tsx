import { airlineName, carrierOf } from './airlines'
import { age, CABIN_LABEL, dayLabel, dayOffset, duration, money, time, usd } from './format'
import { Logo, Timeline, useAwardSegments } from './Timeline'
import type { Places, TrickItem } from './types'

const KIND = {
  return: { label: 'Return ticket', cls: 'bg-good-soft text-good' },
  hidden: { label: 'Hidden city', cls: 'bg-good-soft text-good' },
  joined: { label: 'Joined award', cls: 'bg-award-soft text-award' },
  partner: { label: 'Other provider', cls: 'bg-award-soft text-award' },
  split: { label: 'Split tickets', cls: 'bg-brand-soft text-brand' },
}
const TONE = { fresh: 'text-good', aging: 'text-warn', stale: 'text-bad' }

const Risk = ({ title, lines }: { title: string; lines: string[] }) => (
  <div className="rounded-lg bg-warn/10 p-3 text-xs">
    <p className="mb-1 font-medium text-warn">{title}</p>
    <ul className="list-disc space-y-0.5 pl-4 text-sub">{lines.map((l) => <li key={l}>{l}</li>)}</ul>
  </div>
)

export function TrickRow({ t, places, open, onToggle }: { t: TrickItem; places: Places; open: boolean; onToggle: () => void }) {
  const it = t.trick?.itinerary
  const a = t.award
  const r = t.route
  const dep = it?.departs_at ?? r?.departs_at ?? a?.departs_at
  const arr = it?.arrives_at ?? r?.arrives_at ?? a?.arrives_at
  const mins = it?.duration_minutes ?? r?.duration_minutes ?? a?.duration_minutes
  const stops = it?.stops ?? r?.stops ?? a?.stops
  const via = it?.via ?? r?.via ?? a?.via ?? []
  const codes = it ? [...new Set(it.segments.map((s) => carrierOf(s.flight_number)))] : r?.carriers ?? a?.carriers ?? []
  const k = KIND[t.kind]
  const award = useAwardSegments(a && !r?.segments ? a.legs : null, open)
  const saving = t.compareUsd !== null && t.compareUsd > t.usd ? t.compareUsd - t.usd : null
  const ag = a ? age(a.data_age_hours) : null

  return (
    <li className={open ? 'bg-hover/40' : ''}>
      <button className="grid w-full grid-cols-[2.25rem_1fr_auto] items-center gap-x-4 gap-y-1.5 px-4 py-3.5 text-left hover:bg-hover/60 lg:grid-cols-[2.25rem_1.3fr_0.9fr_1.8fr_auto_1.5rem] lg:px-6"
        onClick={onToggle} aria-expanded={open}>
        {codes.length ? <Logo codes={codes} /> : <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-soft text-brand">⇄</span>}
        <div className="min-w-0">
          {dep && arr ? (
            <div className="text-base font-medium tabular-nums">{time(dep)} – {time(arr)}{dayOffset(dep, arr) > 0 && <sup className="ml-0.5 text-[11px] font-normal">+{dayOffset(dep, arr)}</sup>}</div>
          ) : <div className="text-base font-medium">{t.title}</div>}
          <div className="truncate text-xs text-sub">{codes.length ? codes.map(airlineName).join(', ') : t.sub}</div>
        </div>
        <div className="hidden lg:block">
          {mins != null && <div className="text-base tabular-nums">{duration(mins)}</div>}
          {stops != null && <div className="truncate text-xs text-sub">{stops === 0 ? 'Nonstop' : `${stops} stop${stops > 1 ? 's' : ''} · ${via.join(', ')}`}</div>}
        </div>
        <div className="col-span-2 col-start-2 min-w-0 lg:col-span-1 lg:col-start-auto">
          <span className={`mr-2 inline-block rounded px-1.5 py-0.5 text-xs font-medium ${k.cls}`}>{k.label}</span>
          <span className="text-xs text-sub">{CABIN_LABEL[t.cabin]}{ag && <span className={`ml-1.5 ${TONE[ag.tone]}`}>· {ag.label.replace('checked ', '')}</span>}</span>
          {dep && <div className="truncate text-sm">{t.title}</div>}
          <div className="truncate text-xs text-sub lg:hidden">{mins != null && duration(mins)}{stops != null && ` · ${stops === 0 ? 'nonstop' : `${stops} stop${stops > 1 ? 's' : ''}`}`}</div>
        </div>
        <div className="col-start-3 row-span-2 row-start-1 self-start text-right lg:col-start-auto lg:row-auto lg:self-center">
          {a ? (
            <>
              <div className="text-base font-medium tabular-nums text-award">{a.miles.toLocaleString('en-US')} <span className="text-xs font-normal">mi</span></div>
              <div className="text-xs text-sub tabular-nums">≈ {usd(t.usd)} in all</div>
            </>
          ) : <div className="text-base font-medium tabular-nums text-good">{usd(t.usd)}</div>}
          {saving !== null && <div className="text-xs text-sub tabular-nums"><s>{usd(t.compareUsd!)}</s></div>}
        </div>
        <span className={`hidden text-sub transition lg:block ${open ? 'rotate-180' : ''}`} aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m6 9 6 6 6-6" /></svg>
        </span>
      </button>

      {open && (
        <div className="grid gap-6 border-t border-line px-4 py-5 lg:grid-cols-[1fr_22rem] lg:px-6 lg:pl-[4.75rem]">
          <div>
            {dep && <p className="mb-4 text-sm text-sub">{dayLabel(dep, true)} · {CABIN_LABEL[t.cabin]}</p>}
            {it && <Timeline places={places} segs={it.segments.map((s) => ({ ...s, note: s.travel_class }))} />}
            {!it && r?.segments && <Timeline places={places} segs={r.segments} />}
            {!it && !r?.segments && a && <Timeline places={places} segs={award.segments} />}
            {t.parts && <ul className="space-y-2">{t.parts.map((p) => <li key={p} className="rounded-lg border border-line p-3">{p}</li>)}</ul>}
          </div>
          <div className="space-y-3 text-sm">
            <div className="rounded-lg border border-line p-3">
              <p className="font-medium">{t.title}</p>
              <p className="text-sub">{t.sub}</p>
              {a && <p className="mt-1 tabular-nums">{a.miles.toLocaleString('en-US')} miles + {a.taxes_currency && a.taxes_currency !== 'mixed' ? money(a.taxes, a.taxes_currency) : `≈ ${usd(a.taxes_usd)}`}</p>}
              {a && a.legs.length > 1 && a.legs.map((l, i) => (
                <p key={i} className="text-xs text-sub tabular-nums">{l.origin}–{l.destination}: {l.miles.toLocaleString('en-US')} mi + {money(l.taxes, l.taxes_currency ?? 'USD')}</p>
              ))}
              {saving !== null && <p className="mt-1 text-good">Saves {usd(saving)} against {usd(t.compareUsd!)}{t.kind === 'joined' ? ' (lowest cash fare in this cabin)' : ''}</p>}
              {t.reach && <p className={`mt-1 ${t.reach.status === 'short' ? 'text-sub' : 'text-good'}`}>{t.reach.text}</p>}
              {ag && <p className={`mt-1 text-xs ${TONE[ag.tone]}`}>Seats {ag.label}{a!.seats ? ` · ${a!.seats} left` : ''}</p>}
            </div>
            {t.kind === 'hidden' && (
              <Risk title={`You leave at ${it!.segments.at(-1)!.destination} and do not take ${t.trick!.dropped.map((s) => s.flight_number).join(', ')}`} lines={[
                `Cabin bags only. A checked bag goes to ${t.trick!.ticketed_to}.`,
                'Book this as a one-way ticket. The airline cancels all later flights on the ticket.',
                "This breaks the airline's ticket rules. The airline can close your loyalty account or ask for the fare difference.",
                'If the airline changes the route, the stop at your city can go away.',
              ]} />
            )}
            {t.kind === 'return' && (
              <Risk title={`Return ticket, back on ${dayLabel(t.trick!.return_date!)}. You fly the outbound only`} lines={[
                'Fly the first direction, then do not take the return.',
                'This breaks the ticket rules of most airlines. The risk is low for one ticket and increases if you repeat it with one airline.',
                'This search checked returns 7 and 14 days after departure. Other dates can cost less.',
              ]} />
            )}
            {t.kind === 'joined' && a?.note && <p className="rounded-lg bg-award-soft p-3 text-xs text-award">{a.note}</p>}
            {t.kind === 'split' && <Risk title="Two separate tickets" lines={['A change or cancellation of one ticket does not protect the other.', 'Check the fare rules of each ticket.']} />}
            <div className="flex flex-wrap gap-2">
              {(award.links.length ? award.links : a ? [{ label: `Open ${a.program_name}`, link: a.book_url, primary: true }] : []).map((b) => (
                <a key={b.label} href={b.link} target="_blank" rel="noreferrer" className={`rounded-full px-4 py-1.5 font-medium ${b.primary ? 'bg-brand text-page' : 'border border-line text-brand hover:bg-hover'}`}>{b.label}</a>
              ))}
              {it && (
                <a className="rounded-full bg-brand px-4 py-1.5 font-medium text-page" target="_blank" rel="noreferrer"
                  href={`https://www.google.com/travel/flights?q=${encodeURIComponent(t.kind === 'return'
                    ? `round trip flight ${it.segments[0].origin} to ${it.segments.at(-1)!.destination} on ${it.departs_at.slice(0, 10)} return ${t.trick!.return_date} ${CABIN_LABEL[t.cabin]}`
                    : `one way flight ${it.segments[0].origin} to ${t.trick!.ticketed_to} on ${it.departs_at.slice(0, 10)} ${CABIN_LABEL[t.cabin]}`)}`}>Open in Google Flights</a>
              )}
            </div>
          </div>
        </div>
      )}
    </li>
  )
}
