import { airlineName, carrierOf } from './airlines'
import { CABIN_LABEL, dayLabel, miles, usd } from './format'
import type { AwardOption, AwardSearchResult, Cabin, CashAll, Reach, TransferData, TrickResult, Wallet, Way } from './types'

const CABINS: Cabin[] = ['economy', 'premium', 'business', 'first']
const norm = (f: string) => f.replace(/\s+/g, '').toUpperCase()
const GROUND = /\b(bus|train|rail)\b|surface/i

/** Rank value: lower is better. Money first, then time, stops and old data. */
function score(estUsd: number, minutes: number, stops: number, ageHours: number): number {
  return estUsd + (minutes / 60) * 20 + stops * 40 + (ageHours > 24 * 7 ? 150 : ageHours > 24 ? 30 : 0)
}

function awardWay(o: AwardOption, centsPerMile: number): Way {
  const flights = o.legs.flatMap((l) => l.flight_numbers.map(norm))
  const estUsd = (o.miles * centsPerMile) / 100 + o.taxes_usd
  return {
    id: o.id,
    method: o.kind === 'joined' ? 'joined' : 'award',
    cabin: o.cabin,
    departs_at: o.departs_at,
    arrives_at: o.arrives_at,
    duration_minutes: o.duration_minutes,
    stops: o.stops,
    via: o.via,
    carriers: o.carriers,
    flights,
    ground: o.legs.some((l) => l.aircraft.some((a) => GROUND.test(a))),
    estUsd,
    score: score(estUsd, o.duration_minutes, o.stops, o.data_age_hours),
    cpp: null,
    cashRef: null,
    award: o,
  }
}

export function reachOf(o: AwardOption, wallet: Wallet, transfers: TransferData | null): Reach | null {
  const have = wallet.programs[o.program] ?? 0
  if (have >= o.miles) return { status: 'have', text: `In your wallet: ${miles(have)} ${o.program_name} miles` }
  const gap = o.miles - have
  let short: Reach | null = have > 0 ? { status: 'short', text: `You have ${miles(have)} of ${miles(o.miles)} miles` } : null
  for (const c of transfers?.currencies ?? []) {
    const ratio = c.partners[o.program]
    const bal = wallet.currencies[c.id] ?? 0
    if (!ratio || bal <= 0) continue
    const need = Math.ceil(gap * ratio)
    if (bal >= need) return { status: 'transfer', text: `Move ${miles(need)} ${c.name} points (${ratio}:1)` }
    short ??= { status: 'short', text: `${c.name}: you have ${miles(bal)} of ${miles(need)} points` }
  }
  return short
}

export function buildWays(
  awards: AwardSearchResult | null, cash: CashAll | null, cashDate: string, centsPerMile: number,
  tricks: TrickResult[] = [], wallet: Wallet | null = null, transfers: TransferData | null = null,
): Way[] {
  const ways: Way[] = []
  const cashByFlights = new Map<string, number>()
  const cashLowest: Partial<Record<Cabin, number>> = {}

  for (const cabin of CABINS) {
    const res = cash?.cabins[cabin]
    if (!res) continue
    res.itineraries.forEach((it, i) => {
      if (it.price == null) return
      const flights = it.segments.map((s) => norm(s.flight_number))
      const key = cabin + '|' + flights.join('+')
      cashByFlights.set(key, Math.min(cashByFlights.get(key) ?? Infinity, it.price))
      cashLowest[cabin] = Math.min(cashLowest[cabin] ?? Infinity, it.price)
      ways.push({
        id: `cash:${cabin}:${flights.join('+')}:${i}`,
        method: 'cash',
        cabin,
        departs_at: it.departs_at,
        arrives_at: it.arrives_at,
        duration_minutes: it.duration_minutes,
        stops: it.stops,
        via: it.via,
        carriers: [...new Set(it.segments.map((s) => carrierOf(s.flight_number)))],
        flights,
        ground: it.segments.some((s) => GROUND.test(s.aircraft ?? '')),
        estUsd: it.price,
        score: score(it.price, it.duration_minutes, it.stops, 0),
        cpp: null,
        cashRef: null,
        cash: it,
      })
    })
  }

  for (const o of awards?.options ?? []) {
    const w = awardWay(o, centsPerMile)
    if (o.departs_at.startsWith(cashDate)) {
      // Value of the miles: what the same seat costs in cash, less the award taxes.
      const ref = cashByFlights.get(o.cabin + '|' + w.flights.join('+')) ?? cashLowest[o.cabin]
      if (ref !== undefined && ref > o.taxes_usd) {
        w.cashRef = ref
        w.cpp = ((ref - o.taxes_usd) / o.miles) * 100
      }
    }
    if (wallet) w.reach = reachOf(o, wallet, transfers)
    ways.push(w)
  }

  for (const res of tricks) {
    res.tricks.forEach((t, i) => {
      const it = t.itinerary
      const flights = it.segments.map((s) => norm(s.flight_number))
      ways.push({
        id: `${t.kind}:${t.cabin}:${flights.join('+')}:${i}`,
        method: t.kind,
        cabin: t.cabin,
        departs_at: it.departs_at,
        arrives_at: it.arrives_at,
        duration_minutes: it.duration_minutes,
        stops: it.stops,
        via: it.via,
        carriers: [...new Set(it.segments.map((s) => carrierOf(s.flight_number)))],
        flights,
        ground: false,
        estUsd: t.price,
        // A trick has a cost in risk and effort: rank it a little lower than a plain fare of the same price.
        score: score(t.price, it.duration_minutes, it.stops, 0) + (t.kind === 'hidden' ? 60 : 25),
        cpp: null,
        cashRef: t.normal_price,
        cash: it,
        trick: t,
      })
    })
  }
  return ways
}

export interface Find {
  key: string
  title: string
  headline: string
  detail: string
  tone: 'good' | 'award' | 'brand'
  wayId?: string
  day?: string
  cabin?: Cabin
}

const carriers = (w: Way) => w.carriers.map(airlineName).join(' + ')

/** The short list of things worth a look, found across cabins, dates and payment types. */
export function buildFinds(ways: Way[], day: string, cabin: Cabin | 'any', cash: CashAll | null): Find[] {
  const finds: Find[] = []
  const onDay = ways.filter((w) => w.departs_at.startsWith(day))
  const inCabin = (list: Way[], c: Cabin | 'any') => (c === 'any' ? list : list.filter((w) => w.cabin === c))
  const min = <T,>(list: T[], f: (x: T) => number) => list.reduce<T | undefined>((b, x) => (b === undefined || f(x) < f(b) ? x : b), undefined)
  const awards = (list: Way[]) => list.filter((w) => w.award)
  const focus: Cabin = cabin === 'any' ? 'business' : cabin
  const label = CABIN_LABEL[focus]

  const cheapestAward = min(awards(inCabin(onDay, focus)), (w) => w.estUsd)
  if (cheapestAward?.award) {
    const a = cheapestAward.award
    finds.push({
      key: 'cheap-award', tone: 'award', title: `Lowest ${label.toLowerCase()} award`,
      headline: `${miles(a.miles)} miles + ${usd(a.taxes_usd)}`,
      detail: `${a.program_name} · ${carriers(cheapestAward)}${a.stops ? ` · via ${a.via.join(', ')}` : ' · nonstop'}`,
      wayId: cheapestAward.id, day, cabin: focus,
    })
  }

  const nonstop = min(awards(inCabin(onDay, focus)).filter((w) => w.stops === 0), (w) => w.estUsd)
  if (nonstop?.award && nonstop.id !== cheapestAward?.id) {
    finds.push({
      key: 'nonstop', tone: 'award', title: `Nonstop ${label.toLowerCase()} on miles`,
      headline: `${miles(nonstop.award.miles)} miles + ${usd(nonstop.award.taxes_usd)}`,
      detail: `${nonstop.award.program_name} · ${carriers(nonstop)}`,
      wayId: nonstop.id, day, cabin: focus,
    })
  }

  const bestValue = ways.filter((w) => w.cpp !== null && w.cabin === focus).sort((a, b) => b.cpp! - a.cpp!)[0]
  if (bestValue?.award && bestValue.cpp! >= 1.5) {
    finds.push({
      key: 'value', tone: 'good', title: 'Best value for miles',
      headline: `${bestValue.cpp!.toFixed(1)}¢ per mile`,
      detail: `${bestValue.award.program_name}: ${miles(bestValue.award.miles)} miles in place of ${usd(bestValue.cashRef!)}`,
      wayId: bestValue.id, day, cabin: focus,
    })
  }

  // A higher cabin on miles for less than the cash fare of a lower cabin.
  const lowerCash = min(onDay.filter((w) => w.cash && !w.trick && CABINS.indexOf(w.cabin) < CABINS.indexOf(focus)), (w) => w.estUsd)
  if (cheapestAward && lowerCash && cheapestAward.estUsd < lowerCash.estUsd) {
    finds.push({
      key: 'upgrade', tone: 'good', title: `${label} for less than ${CABIN_LABEL[lowerCash.cabin].toLowerCase()}`,
      headline: `≈ ${usd(cheapestAward.estUsd)} vs ${usd(lowerCash.estUsd)}`,
      detail: `Award in ${label.toLowerCase()} costs less than the lowest ${CABIN_LABEL[lowerCash.cabin].toLowerCase()} cash fare`,
      wayId: cheapestAward.id, day, cabin: focus,
    })
  }

  const trick = min(inCabin(onDay, focus).filter((w) => w.trick), (w) => w.estUsd)
  if (trick?.trick) {
    const t = trick.trick
    finds.unshift({
      key: 'trick', tone: 'good',
      title: t.kind === 'hidden' ? `Ticket to ${t.ticketed_to}, leave at the stop` : 'Return ticket costs less than one way',
      headline: `${usd(t.price)} in place of ${usd(t.normal_price)}`,
      detail: `${carriers(trick)} · ${label.toLowerCase()} · you save ${usd(t.saving)}`,
      wayId: trick.id, day, cabin: focus,
    })
  }

  const mine = min(awards(inCabin(onDay, focus)).filter((w) => w.reach && w.reach.status !== 'short'), (w) => w.estUsd)
  if (mine?.award && mine.id !== cheapestAward?.id) {
    finds.push({
      key: 'mine', tone: 'award', title: 'Lowest award with your points',
      headline: `${miles(mine.award.miles)} miles + ${usd(mine.award.taxes_usd)}`,
      detail: mine.reach!.text,
      wayId: mine.id, day, cabin: focus,
    })
  }

  const cashCheap = min(inCabin(onDay, focus).filter((w) => w.cash && !w.trick), (w) => w.estUsd)
  const level = cash?.cabins[focus]?.price_level
  if (cashCheap) {
    finds.push({
      key: 'cash', tone: 'brand', title: `Lowest ${label.toLowerCase()} cash fare`,
      headline: usd(cashCheap.estUsd),
      detail: `${carriers(cashCheap)}${level ? ` · prices are ${level}` : ''}`,
      wayId: cashCheap.id, day, cabin: focus,
    })
  }

  // Another date in the window that is at least 10% cheaper.
  if (cheapestAward) {
    const other = min(awards(inCabin(ways, focus)).filter((w) => !w.departs_at.startsWith(day)), (w) => w.estUsd)
    if (other?.award && other.estUsd < cheapestAward.estUsd * 0.9) {
      const d = other.departs_at.slice(0, 10)
      finds.push({
        key: 'date', tone: 'brand', title: `${dayLabel(d)} costs less`,
        headline: `${miles(other.award.miles)} miles + ${usd(other.award.taxes_usd)}`,
        detail: `${other.award.program_name} · ${carriers(other)}`,
        wayId: other.id, day: d, cabin: focus,
      })
    }
  }
  return finds
}
