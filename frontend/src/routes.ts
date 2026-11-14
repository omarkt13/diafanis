import { airlineName, carrierOf } from './airlines'
import { CABIN_LABEL, miles, usd } from './format'
import type { AwardOption, AwardSearchResult, Cabin, CashAll, Offer, Ranked, Reach, Route, TransferData, TrickItem, TrickResult, Wallet } from './types'

export const CABINS: Cabin[] = ['economy', 'premium', 'business', 'first']
// "EK 083", "EK083" and "EK83" are one flight.
const norm = (f: string) => f.replace(/\s+/g, '').toUpperCase().replace(/^([A-Z0-9]{2})0+(\d)/, '$1$2')
const GROUND = /\b(bus|train|rail)\b|surface/i

/** Parameters of the "Best value" view. */
export const VALUE = {
  worth: { economy: 1, premium: 1.5, business: 3, first: 4.5 } as Record<Cabin, number>, // what a seat is worth against economy
  perExtraHour: 15, // dollars for each hour slower than the fastest route
  perStop: 30,
  staleWeek: 80, // award data older than 7 days
  staleDay: 20, // award data older than 1 day
  surprise: { premium: 1.4, business: 2.5, first: 4 } as Record<string, number>, // "surprisingly cheap" below this multiple of economy
  goodCentsPerMile: 2,
  partnerSaving: 0.75, // partner award counts as a trick when it costs less than this share of the cash fare
}

// Airlines that each program belongs to. An award on another airline is a "partner" award.
const HOME: Record<string, string[]> = {
  aeroplan: ['AC'], united: ['UA'], lufthansa: ['LH', 'LX', 'OS', 'SN', 'EN', 'EW'], turkish: ['TK'], singapore: ['SQ'],
  american: ['AA'], alaska: ['AS', 'HA'], qantas: ['QF'], qatar: ['QR'], cathay: ['CX'], delta: ['DL'], flyingblue: ['AF', 'KL'],
  virginatlantic: ['VS'], saudia: ['SV'], aeromexico: ['AM'], emirates: ['EK', 'FZ'], etihad: ['EY'], jetblue: ['B6'],
  smiles: ['G3'], velocity: ['VA'], eurobonus: ['SK'], connectmiles: ['CM'], azul: ['AD'],
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

export const awardUsd = (o: AwardOption, cpm: number) => (o.miles * cpm) / 100 + o.taxes_usd

/** Group every fare by the flights it is for. Joined awards are kept apart: they are tricks. */
export function buildRoutes(
  awards: AwardSearchResult | null, cash: CashAll | null, cpm: number, wallet: Wallet, transfers: TransferData | null,
): { routes: Route[]; joined: AwardOption[]; cashLowest: Partial<Record<Cabin, number>> } {
  const map = new Map<string, Route>()
  const cashLowest: Partial<Record<Cabin, number>> = {}
  let cashDay = ''

  for (const cabin of CABINS) {
    const res = cash?.cabins[cabin]
    if (!res) continue
    for (const it of res.itineraries) {
      if (it.price == null || !it.segments.length) continue
      const flights = it.segments.map((s) => norm(s.flight_number))
      const day = it.departs_at.slice(0, 10)
      cashDay = day
      const key = `${day}|${flights.join('+')}`
      let r = map.get(key)
      if (!r) {
        r = {
          key, day, origin: it.segments[0].origin, destination: it.segments.at(-1)!.destination, flights,
          carriers: [...new Set(it.segments.map((s) => carrierOf(s.flight_number)))],
          departs_at: it.departs_at, arrives_at: it.arrives_at, duration_minutes: it.duration_minutes, stops: it.stops, via: it.via,
          ground: it.segments.some((s) => GROUND.test(s.aircraft ?? '')),
          segments: it.segments.map((s) => ({ ...s, note: null })), legs: null, offers: [],
        }
        map.set(key, r)
      }
      cashLowest[cabin] = Math.min(cashLowest[cabin] ?? Infinity, it.price)
      const old = r.offers.find((o) => o.kind === 'cash' && o.cabin === cabin)
      const below = !!res.typical_range && it.price < res.typical_range[0]
      if (!old) r.offers.push({ id: `${key}|cash|${cabin}`, cabin, kind: 'cash', usd: it.price, cpp: null, cashRef: null, reach: null, partner: false, belowTypical: below })
      else if (it.price < old.usd) { old.usd = it.price; old.belowTypical = below }
    }
  }

  const joined: AwardOption[] = []
  for (const o of awards?.options ?? []) {
    if (o.kind === 'joined') { joined.push(o); continue }
    const flights = o.legs.flatMap((l) => l.flight_numbers.map(norm))
    const day = o.departs_at.slice(0, 10)
    const key = `${day}|${flights.join('+')}`
    let r = map.get(key)
    if (!r) {
      r = {
        key, day, origin: o.origin, destination: o.destination, flights, carriers: o.carriers, departs_at: o.departs_at,
        arrives_at: o.arrives_at, duration_minutes: o.duration_minutes, stops: o.stops, via: o.via,
        ground: o.legs.some((l) => l.aircraft.some((a) => GROUND.test(a))), segments: null, legs: o.legs, offers: [],
      }
      map.set(key, r)
    }
    r.legs ??= o.legs
    const cashSame = r.offers.find((x) => x.kind === 'cash' && x.cabin === o.cabin)?.usd
    const ref = cashSame ?? (day === cashDay ? cashLowest[o.cabin] : undefined)
    const offer: Offer = {
      id: `${key}|${o.program}|${o.cabin}`, cabin: o.cabin, kind: 'award', usd: awardUsd(o, cpm), award: o,
      cpp: ref !== undefined && ref > o.taxes_usd ? ((ref - o.taxes_usd) / o.miles) * 100 : null, cashRef: ref ?? null,
      reach: reachOf(o, wallet, transfers), partner: !(HOME[o.program] ?? []).some((c) => r!.carriers.includes(c)), belowTypical: false,
    }
    const i = r.offers.findIndex((x) => x.kind === 'award' && x.cabin === o.cabin && x.award!.program === o.program)
    if (i < 0) r.offers.push(offer)
    else if (offer.usd < r.offers[i].usd) r.offers[i] = offer
  }
  return { routes: [...map.values()], joined, cashLowest }
}

export interface Shape {
  cabins: Cabin[]
  pay: ('cash' | 'award')[]
  maxStops: number
  programs: string[]
  airlines: string[]
  maxHours: number
  maxAgeDays: number
  onlyMine: boolean
}

const ageOk = (o: AwardOption, f: Shape) => !f.maxAgeDays || (o.data_age_hours >= 0 && o.data_age_hours <= f.maxAgeDays * 24)
const awardOk = (o: AwardOption, reach: Reach | null, f: Shape) =>
  f.cabins.includes(o.cabin) && (!f.programs.length || f.programs.includes(o.program)) && ageOk(o, f) && (!f.onlyMine || (!!reach && reach.status !== 'short'))

export function filterRoutes(routes: Route[], f: Shape, day: string): Route[] {
  const out: Route[] = []
  for (const r of routes) {
    if (r.day !== day || r.stops > f.maxStops) continue
    if (f.airlines.length && !r.carriers.some((c) => f.airlines.includes(c))) continue
    if (f.maxHours && r.duration_minutes > f.maxHours * 60) continue
    const offers = r.offers.filter((o) =>
      o.kind === 'cash' ? f.pay.includes('cash') && f.cabins.includes(o.cabin) && !f.programs.length && !f.onlyMine : f.pay.includes('award') && awardOk(o.award!, o.reach, f))
    if (offers.length) out.push({ ...r, offers })
  }
  return out
}

const cheapest = (offers: Offer[]) => offers.reduce((b, o) => (o.usd < b.usd ? o : b))

export function rankLowest(routes: Route[]): Ranked[] {
  return routes
    .map((route) => ({ route, pick: cheapest(route.offers), reasons: [], score: 0 }))
    .map((r) => ({ ...r, score: r.pick.usd }))
    .sort((a, b) => a.score - b.score || a.route.duration_minutes - b.route.duration_minutes)
}

export function rankValue(routes: Route[]): Ranked[] {
  if (!routes.length) return []
  const fastest = Math.min(...routes.map((r) => r.duration_minutes))
  const all = routes.flatMap((r) => r.offers)
  const econCash = all.filter((o) => o.cabin === 'economy' && o.kind === 'cash')
  const econ = econCash.length ? econCash : all.filter((o) => o.cabin === 'economy')
  const econRef = econ.length ? Math.min(...econ.map((o) => o.usd)) : null

  return routes.map((route) => {
    const base = ((route.duration_minutes - fastest) / 60) * VALUE.perExtraHour + route.stops * VALUE.perStop
    let best: { o: Offer; adj: number } | null = null
    for (const o of route.offers) {
      const age = o.award?.data_age_hours ?? 0
      const adj = o.usd / VALUE.worth[o.cabin] + base + (age > 168 ? VALUE.staleWeek : age > 24 ? VALUE.staleDay : 0)
      if (!best || adj < best.adj) best = { o, adj }
    }
    const pick = best!.o
    const reasons: string[] = []
    if (pick.cabin !== 'economy' && econRef) {
      const ratio = pick.usd / econRef
      if (ratio < 1) reasons.push(`${CABIN_LABEL[pick.cabin]} for less than economy`)
      else if (ratio <= VALUE.surprise[pick.cabin]) reasons.push(`${CABIN_LABEL[pick.cabin]} for ${ratio.toFixed(1)}× economy`)
    }
    if (route.stops === 0) reasons.push('Nonstop')
    else if (route.duration_minutes === fastest) reasons.push('Fastest')
    if (pick.cpp !== null && pick.cpp >= VALUE.goodCentsPerMile) reasons.push(`${pick.cpp.toFixed(1)}¢ per mile`)
    if (pick.belowTypical) reasons.push('Below the usual price')
    if (pick.reach && pick.reach.status !== 'short') reasons.push('Your points')
    return { route, pick, reasons, score: best!.adj }
  }).sort((a, b) => a.score - b.score)
}

/** The tricks view: other ways to buy the trip. Always in order of cost. */
export function buildTricks(
  routes: Route[], joined: AwardOption[], results: TrickResult[], cashLowest: Partial<Record<Cabin, number>>,
  f: Shape, day: string, cpm: number, wallet: Wallet, transfers: TransferData | null, extra: TrickItem[] = [],
): TrickItem[] {
  const items: TrickItem[] = [...extra.filter((x) => f.cabins.includes(x.cabin))]
  const names = (codes: string[]) => codes.map(airlineName).join(' + ')

  if (f.pay.includes('award')) {
    for (const o of joined) {
      const reach = reachOf(o, wallet, transfers)
      if (!o.departs_at.startsWith(day) || o.stops > f.maxStops || !awardOk(o, reach, f)) continue
      if (f.airlines.length && !o.carriers.some((c) => f.airlines.includes(c))) continue
      if (f.maxHours && o.duration_minutes > f.maxHours * 60) continue
      items.push({
        id: 'joined|' + o.id, kind: 'joined', cabin: o.cabin, usd: awardUsd(o, cpm), compareUsd: cashLowest[o.cabin] ?? null,
        title: `Two award legs joined at ${o.legs[0].destination}`, sub: `${o.program_name} · ${names(o.carriers)}`, award: o, reach,
      })
    }
    for (const r of filterRoutes(routes, f, day)) {
      for (const cabin of f.cabins) {
        const cash = r.offers.find((o) => o.kind === 'cash' && o.cabin === cabin)
        const partner = r.offers.filter((o) => o.kind === 'award' && o.cabin === cabin && o.partner)
        if (!cash || !partner.length) continue
        const best = cheapest(partner)
        if (best.usd > cash.usd * VALUE.partnerSaving) continue
        items.push({
          id: 'partner|' + best.id, kind: 'partner', cabin, usd: best.usd, compareUsd: cash.usd,
          title: `${names(r.carriers)} seat through ${best.award!.program_name}`,
          sub: `${miles(best.award!.miles)} miles + ${usd(best.award!.taxes_usd)} in place of the ${usd(cash.usd)} fare`, route: r, offer: best, award: best.award, reach: best.reach,
        })
      }
    }
  }

  if (f.pay.includes('cash') && !f.programs.length && !f.onlyMine) {
    for (const res of results) {
      res.tricks.forEach((t, i) => {
        const it = t.itinerary
        if (!f.cabins.includes(t.cabin) || !it.departs_at.startsWith(day) || it.stops > f.maxStops) return
        if (f.maxHours && it.duration_minutes > f.maxHours * 60) return
        const codes = [...new Set(it.segments.map((s) => carrierOf(s.flight_number)))]
        if (f.airlines.length && !codes.some((c) => f.airlines.includes(c))) return
        items.push({
          id: `${t.kind}|${t.cabin}|${i}|${it.departs_at}`, kind: t.kind, cabin: t.cabin, usd: t.price, compareUsd: t.normal_price,
          title: t.kind === 'hidden' ? `Ticket to ${t.ticketed_to}, leave at ${it.segments.at(-1)!.destination}` : 'Return ticket, fly one way',
          sub: names(codes), trick: t,
        })
      })
    }
  }
  return items.sort((a, b) => a.usd - b.usd)
}
