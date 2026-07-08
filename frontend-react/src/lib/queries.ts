import { apiFetch } from '@/lib/api'
import type { FundDetail, FundListItem, ProviderDetail, ProviderListItem, SeriesPoint } from '@/lib/types'

export const keys = {
  providers: (assetClass?: string) => ['providers', assetClass ?? 'all'] as const,
  provider: (slug: string) => ['provider', slug] as const,
  funds: (params: string) => ['funds', params] as const,
  fund: (id: number) => ['fund', id] as const,
  series: (id: number) => ['fund', id, 'series'] as const,
}

export function listProviders(assetClass?: string) {
  const qs = assetClass ? `?asset_class=${assetClass}` : ''
  return apiFetch<ProviderListItem[]>(`/providers${qs}`)
}

export function getProvider(slug: string) {
  return apiFetch<ProviderDetail>(`/providers/${slug}`)
}

export function searchFunds(params: { q?: string; asset_class?: string }) {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.asset_class) search.set('asset_class', params.asset_class)
  const qs = search.toString()
  return apiFetch<FundListItem[]>(`/funds${qs ? `?${qs}` : ''}`)
}

export function getFund(id: number) {
  return apiFetch<FundDetail>(`/funds/${id}`)
}

export function getFundSeries(id: number) {
  return apiFetch<SeriesPoint[]>(`/funds/${id}/series`)
}
