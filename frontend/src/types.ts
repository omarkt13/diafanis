export type Cabin = 'economy' | 'premium' | 'business' | 'first'
export type Method = 'cash' | 'award' | 'joined' | 'return' | 'hidden'

export interface Leg {
  availability_id: string
  flight_numbers: string[]
  origin: string
  destination: string
  connections: string[]
  departs_at: string
  arrives_at: string
  duration_minutes: number
  carriers: string[]
  aircraft: string[]
  fare_classes: string[]
  miles: number
  taxes: number
  taxes_currency: string | null
  seats: number | null
  updated_at: string
}

export interface AwardOption {
  id: string
  kind: 'direct' | 'joined'
  program: string
  program_name: string
  alliance: string | null
  book_url: string
  cabin: Cabin
  origin: string
  destination: string
  departs_at: string
  arrives_at: string
  duration_minutes: number
  stops: number
  via: string[]
  carriers: string[]
  miles: number
  taxes: number
  taxes_currency: string | null
  taxes_usd: number
  seats: number | null
  data_age_hours: number
  legs: Leg[]
  note: string | null
}

export interface AwardSearchResult {
  origin: string
  destination: string
  dates: string[]
  hubs: string[]
  options: AwardOption[]
  api_calls: number
  rate_limit_remaining: number | null
}

export interface CashSegment {
  flight_number: string
  airline: string
  origin: string
  destination: string
  departs_at: string
  arrives_at: string
  duration_minutes: number
  aircraft: string | null
  travel_class: string | null
}

export interface CashItinerary {
  price: number | null
  currency: string
  departs_at: string
  arrives_at: string
  duration_minutes: number
  stops: number
  via: string[]
  airlines: string[]
  best: boolean
  segments: CashSegment[]
}

export interface CashSearchResult {
  itineraries: CashItinerary[]
  lowest_price: number | null
  price_level: string | null
  typical_range: number[] | null
  currency: string
}

export interface CashAll {
  cabins: Partial<Record<Cabin, CashSearchResult>>
  errors: Partial<Record<Cabin, string>>
}

export interface SearchParams {
  origin: string
  destination: string
  date: string
  flex: number
}

export interface Segment {
  flight_number: string
  origin: string
  destination: string
  departs_at: string
  arrives_at: string
  duration_minutes: number
  aircraft: string | null
  note?: string | null
}

/** One way to get from A to B: a cash fare, an award, or two joined award legs. */
export interface Way {
  id: string
  method: Method
  cabin: Cabin
  departs_at: string
  arrives_at: string
  duration_minutes: number
  stops: number
  via: string[]
  carriers: string[]
  flights: string[]
  ground: boolean
  estUsd: number
  score: number
  cpp: number | null
  cashRef: number | null
  award?: AwardOption
  cash?: CashItinerary
  trick?: Trick
  reach?: Reach | null
}

export interface Trick {
  kind: 'return' | 'hidden'
  cabin: Cabin
  price: number
  currency: string
  normal_price: number
  saving: number
  same_flights: boolean
  itinerary: CashItinerary
  ticketed_to: string | null
  dropped: CashSegment[]
  return_date: string | null
}

export interface TrickResult {
  cabin: Cabin
  tricks: Trick[]
  beyond: string[]
  api_calls: number
  errors: string[]
}

export interface TransferCurrency { id: string; name: string; note: string; partners: Record<string, number> }
export interface TransferData { currencies: TransferCurrency[]; programs: { id: string; name: string; alliance: string | null }[] }
export interface Wallet { programs: Record<string, number>; currencies: Record<string, number> }

/** How the wallet covers an award. */
export interface Reach {
  status: 'have' | 'transfer' | 'short'
  text: string
}

export type Places = Record<string, { city: string; name: string }>
