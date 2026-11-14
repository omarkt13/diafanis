export type Cabin = 'economy' | 'premium' | 'business' | 'first'

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
  segments: { flight_number: string; airline: string; origin: string; destination: string; departs_at: string; arrives_at: string; aircraft: string | null }[]
}

export interface CashSearchResult {
  itineraries: CashItinerary[]
  lowest_price: number | null
  price_level: string | null
  typical_range: number[] | null
  currency: string
}

export interface SearchParams {
  origin: string
  destination: string
  date: string
  flex: number
}
