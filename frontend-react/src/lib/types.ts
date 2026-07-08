export type AssetClass = 'pe_buyout' | 'vc' | 'real_assets' | 'private_credit'

export const ASSET_CLASS_LABELS: Record<AssetClass, string> = {
  pe_buyout: 'PE Buyout',
  vc: 'Venture Capital',
  real_assets: 'Real Assets & Infra',
  private_credit: 'Private Credit',
}

export interface ProviderListItem {
  id: number
  name: string
  slug: string
  asset_class: AssetClass
  hq: string | null
  aum_busd: number | null
  description: string | null
  fund_count: number
}

export interface FundListItem {
  id: number
  name: string
  vintage_year: number
  fund_size_musd: number | null
  asset_class: AssetClass
  strategy: string | null
  status: string
  provider_name: string
  provider_slug: string
  est_tvpi: number | null
  est_net_irr: number | null
  pme_alpha: number | null
  confidence: string | null
}

export interface ProviderDetail extends Omit<ProviderListItem, 'fund_count'> {
  founded_year: number | null
  funds: FundListItem[]
}

export interface Metrics {
  as_of_date: string
  est_tvpi: number
  est_dpi: number
  est_rvpi: number
  est_nav_musd: number | null
  est_net_irr: number | null
  pme_alpha: number | null
  confidence: string
  narrative: string | null
}

export interface Constituent {
  ticker: string
  weight: number
  trailing_return_1y: number | null
}

export interface Exposure {
  sector_tag: string
  basket_name: string
  weight: number
  constituents: Constituent[]
}

export interface MacroItem {
  key: string
  label: string
  value: number
}

export interface FundDetail {
  id: number
  name: string
  vintage_year: number
  fund_size_musd: number | null
  asset_class: AssetClass
  strategy: string | null
  status: string
  provider_name: string
  provider_slug: string
  reported_tvpi: number | null
  reported_irr: number | null
  reported_as_of: string | null
  reported_source: string | null
  metrics: Metrics | null
  exposures: Exposure[]
  macro: MacroItem[]
}

export interface SeriesPoint {
  period_date: string
  est_tvpi: number
  benchmark_tvpi: number
  est_nav_musd: number | null
}
