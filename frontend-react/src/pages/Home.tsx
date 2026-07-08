import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { FundTable } from '@/components/FundTable'
import { Shell } from '@/components/Shell'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { fmtSize } from '@/lib/format'
import { keys, listProviders, searchFunds } from '@/lib/queries'
import { ASSET_CLASS_LABELS } from '@/lib/types'
import type { AssetClass } from '@/lib/types'
import { cn } from '@/lib/utils'

const TABS: Array<{ value: AssetClass | ''; label: string }> = [
  { value: '', label: 'All' },
  { value: 'pe_buyout', label: ASSET_CLASS_LABELS.pe_buyout },
  { value: 'vc', label: ASSET_CLASS_LABELS.vc },
  { value: 'real_assets', label: ASSET_CLASS_LABELS.real_assets },
  { value: 'private_credit', label: ASSET_CLASS_LABELS.private_credit },
]

export function Home() {
  const [assetClass, setAssetClass] = useState<AssetClass | ''>('')
  const [search, setSearch] = useState('')

  const providersQuery = useQuery({
    queryKey: keys.providers(assetClass || undefined),
    queryFn: () => listProviders(assetClass || undefined),
  })
  const fundSearchQuery = useQuery({
    queryKey: keys.funds(`q=${search}&ac=${assetClass}`),
    queryFn: () => searchFunds({ q: search, asset_class: assetClass || undefined }),
    enabled: search.length >= 2,
  })

  return (
    <Shell>
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight">
          Know what your fund stake is really worth.
        </h1>
        <p className="mt-2 max-w-2xl text-slate-500">
          Daily model-estimated valuations for {'~'}150 flagship private market funds, built from
          public benchmark comps — so holders and secondary buyers can sanity-check the marks
          they're shown.
        </p>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-2">
        {TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setAssetClass(tab.value)}
            className={cn(
              'rounded-full px-4 py-1.5 text-sm font-medium transition-colors',
              assetClass === tab.value
                ? 'bg-slate-900 text-white'
                : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-100',
            )}
          >
            {tab.label}
          </button>
        ))}
        <div className="ml-auto w-full max-w-xs">
          <Input
            placeholder="Search funds or providers…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      {search.length >= 2 ? (
        <Card>
          <CardContent className="p-0">
            {fundSearchQuery.data && fundSearchQuery.data.length > 0 ? (
              <FundTable funds={fundSearchQuery.data} showProvider />
            ) : (
              <p className="p-6 text-sm text-slate-500">
                {fundSearchQuery.isLoading ? 'Searching…' : 'No funds match your search.'}
              </p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {providersQuery.data?.map((provider) => (
            <Link key={provider.id} to={`/providers/${provider.slug}`}>
              <Card className="h-full transition-shadow hover:shadow-md">
                <CardContent className="p-5">
                  <div className="flex items-start justify-between gap-2">
                    <h3 className="font-semibold">{provider.name}</h3>
                    <Badge>{ASSET_CLASS_LABELS[provider.asset_class]}</Badge>
                  </div>
                  <p className="mt-1 line-clamp-2 text-sm text-slate-500">{provider.description}</p>
                  <p className="mt-3 text-xs text-slate-400">
                    {provider.hq} · AUM {provider.aum_busd ? fmtSize(provider.aum_busd * 1000) : '—'} ·{' '}
                    {provider.fund_count} fund{provider.fund_count === 1 ? '' : 's'} tracked
                  </p>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
      {providersQuery.isLoading && !search && (
        <p className="text-sm text-slate-500">Loading providers…</p>
      )}
    </Shell>
  )
}
