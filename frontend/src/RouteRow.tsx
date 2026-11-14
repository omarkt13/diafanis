import { airlineName } from './airlines'
import { age, CABIN_LABEL, dayLabel, dayOffset, duration, miles, money, time, usd } from './format'
import { CABINS } from './routes'
import { Logo, Timeline, useAwardSegments } from './Timeline'
import type { Cabin, Offer, Places, Ranked } from './types'

const SHORT: Record<Cabin, string> = { economy: 'Economy', premium: 'Premium', business: 'Business', first: 'First' }
const TONE = { fresh: 'text-good', aging: 'text-warn', stale: 'text-bad' }
const taxes = (o: Offer) => (o.award!.taxes_currency && o.award!.taxes_currency !== 'mixed' ? money(o.award!.taxes, o.award!.taxes_currency) : `≈ ${usd(o.award!.taxes_usd)}`)

function FareCell({ cabin, offers, pick }: { cabin: Cabin; offers: Offer[]; pick: Offer }) {
  const cash = offers.find((o) => o.kind === 'cash')
  const awards = offers.filter((o) => o.kind === 'award')
  const award = awards.length ? awards.reduce((b, o) => (o.usd < b.usd ? o : b)) : undefined
  const picked = pick.cabin === cabin
  return (
    <div className={`min-w-0 rounded px-1.5 py-1 text-center ${picked ? 'bg-brand-soft ring-1 ring-brand' : ''}`}>
      <div className="text-[10px] tracking-wide text-sub uppercase">{SHORT[cabin]}</div>
      {!cash && !award && <div className="text-sm text-line">–</div>}
      {cash && <div className={`text-sm tabular-nums ${picked && pick.kind === 'cash' ? 'font-semibold' : ''} ${cash.belowTypical ? 'text-good' : ''}`}>{usd(cash.usd)}</div>}
      {award && (
        <div className={`truncate text-sm tabular-nums text-award ${picked && pick.kind === 'award' ? 'font-semibold' : ''}`} title={`${award.award!.program_name}: ${award.award!.miles.toLocaleString('en-US')} miles + ${taxes(award)}`}>
          {miles(award.award!.miles)}<span className="text-[10px]"> mi</span>
        </div>
      )}
    </div>
  )
}

interface Props { r: Ranked; places: Places; open: boolean; onToggle: () => void; view: 'lowest' | 'value' }

export function RouteRow({ r, places, open, onToggle, view }: Props) {
  const { route, pick } = r
  const plus = dayOffset(route.departs_at, route.arrives_at)
  const byCabin = (c: Cabin) => route.offers.filter((o) => o.cabin === c)
  const award = useAwardSegments(route.segments ? null : route.legs, open)
  const links = useAwardSegments(route.legs, open && !!route.segments).links
  const allLinks = award.links.length ? award.links : links

  return (
    <li id={`row-${route.key}`} className={open ? 'bg-hover/40' : ''}>
      <button className="grid w-full grid-cols-[2.25rem_1fr_auto] items-center gap-x-4 gap-y-2 px-4 py-3.5 text-left hover:bg-hover/60 lg:grid-cols-[2.25rem_1.3fr_0.9fr_0.8fr_19rem_1.5rem] lg:px-6"
        onClick={onToggle} aria-expanded={open}>
        <Logo codes={route.carriers} />
        <div className="min-w-0">
          <div className="text-base font-medium tabular-nums">
            {time(route.departs_at)} – {time(route.arrives_at)}{plus > 0 && <sup className="ml-0.5 text-[11px] font-normal">+{plus}</sup>}
          </div>
          <div className="truncate text-xs text-sub">{route.carriers.map(airlineName).join(', ')}{route.ground && ' · includes ground transport'}</div>
        </div>
        <div className="col-start-3 row-start-1 text-right lg:col-start-auto lg:row-auto lg:text-left">
          <div className="text-sm tabular-nums lg:text-base">{duration(route.duration_minutes)}</div>
          <div className="text-xs text-sub">{route.origin}–{route.destination}</div>
        </div>
        <div className="col-span-2 col-start-2 lg:col-span-1 lg:col-start-auto">
          <div className="text-sm lg:text-base">{route.stops === 0 ? 'Nonstop' : `${route.stops} stop${route.stops > 1 ? 's' : ''}`}<span className="text-xs text-sub lg:hidden">{route.via.length > 0 && ` · ${route.via.join(', ')}`}</span></div>
          <div className="hidden truncate text-xs text-sub lg:block">{route.via.join(', ')}</div>
        </div>
        <div className="col-span-3 lg:col-span-1">
          <div className="grid grid-cols-4 gap-1">{CABINS.map((c) => <FareCell key={c} cabin={c} offers={byCabin(c)} pick={pick} />)}</div>
          {view === 'value' && r.reasons.length > 0 && (
            <div className="mt-1 flex flex-wrap justify-end gap-1">
              {r.reasons.map((x) => <span key={x} className="rounded bg-good-soft px-1.5 py-0.5 text-[11px] font-medium text-good">{x}</span>)}
            </div>
          )}
        </div>
        <span className={`hidden text-sub transition lg:block ${open ? 'rotate-180' : ''}`} aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m6 9 6 6 6-6" /></svg>
        </span>
      </button>

      {open && (
        <div className="grid gap-6 border-t border-line px-4 py-5 lg:grid-cols-[1fr_24rem] lg:px-6 lg:pl-[4.75rem]">
          <div>
            <p className="mb-4 text-sm text-sub">{dayLabel(route.departs_at, true)} · {route.flights.join(' · ')}</p>
            <Timeline segs={route.segments ?? award.segments} places={places} />
          </div>
          <div className="space-y-3 text-sm">
            <p className="font-medium">All fares for these flights</p>
            {CABINS.filter((c) => byCabin(c).length).map((c) => (
              <div key={c} className="rounded-lg border border-line">
                <div className="border-b border-line bg-hover/50 px-3 py-1.5 text-xs font-medium tracking-wide text-sub uppercase">{CABIN_LABEL[c]}</div>
                {byCabin(c).sort((a, b) => a.usd - b.usd).map((o) => {
                  const ag = o.award ? age(o.award.data_age_hours) : null
                  return (
                    <div key={o.id} className={`border-b border-line px-3 py-2 last:border-b-0 ${o.id === pick.id ? 'bg-brand-soft/60' : ''}`}>
                      <div className="flex items-baseline justify-between gap-3">
                        <span className="min-w-0 truncate">{o.kind === 'cash' ? 'Cash fare' : o.award!.program_name}{o.partner && <span className="ml-1.5 text-xs text-award">partner award</span>}</span>
                        <span className={`shrink-0 font-medium tabular-nums ${o.kind === 'award' ? 'text-award' : ''}`}>
                          {o.kind === 'cash' ? usd(o.usd) : `${o.award!.miles.toLocaleString('en-US')} mi + ${taxes(o)}`}
                        </span>
                      </div>
                      {o.award && (
                        <div className="mt-0.5 flex flex-wrap gap-x-2 text-xs text-sub">
                          <span>≈ {usd(o.usd)}</span>
                          {o.cpp !== null && <span className="text-good">{o.cpp.toFixed(1)}¢ per mile</span>}
                          <span className={TONE[ag!.tone]}>{ag!.label}{o.award.seats ? ` · ${o.award.seats} left` : ''}</span>
                          {o.reach && <span className={o.reach.status === 'short' ? '' : 'text-good'}>{o.reach.text}</span>}
                        </div>
                      )}
                      {o.kind === 'cash' && !!o.otherCabin?.length && <div className="mt-0.5 text-xs text-warn">Mixed cabin: {o.otherCabin.join(', ')}</div>}
                      {o.kind === 'cash' && o.belowTypical && <div className="mt-0.5 text-xs text-good">Below the usual price for this route</div>}
                    </div>
                  )
                })}
              </div>
            ))}
            <div className="flex flex-wrap gap-2">
              {route.offers.some((o) => o.kind === 'cash') && (
                <a className="rounded-full bg-brand px-4 py-1.5 font-medium text-page" target="_blank" rel="noreferrer"
                  href={`https://www.google.com/travel/flights?q=${encodeURIComponent(`one way flight ${route.origin} to ${route.destination} on ${route.day}`)}`}>Open in Google Flights</a>
              )}
              {allLinks.map((b) => (
                <a key={b.label} href={b.link} target="_blank" rel="noreferrer" className="rounded-full border border-line px-4 py-1.5 font-medium text-brand hover:bg-hover">{b.label}</a>
              ))}
            </div>
            {route.offers.some((o) => o.award) && <p className="text-xs text-sub">Award seats come from a cache. Check them on the program site before you transfer points.</p>}
          </div>
        </div>
      )}
    </li>
  )
}
