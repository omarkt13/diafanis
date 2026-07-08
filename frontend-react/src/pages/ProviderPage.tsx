import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import { FundTable } from '@/components/FundTable'
import { Shell } from '@/components/Shell'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { fmtSize } from '@/lib/format'
import { getProvider, keys } from '@/lib/queries'
import { ASSET_CLASS_LABELS } from '@/lib/types'

export function ProviderPage() {
  const { slug = '' } = useParams()
  const { data: provider, isLoading } = useQuery({
    queryKey: keys.provider(slug),
    queryFn: () => getProvider(slug),
  })

  return (
    <Shell>
      <Link to="/" className="text-sm text-slate-500 hover:underline">
        ← All providers
      </Link>
      {isLoading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {provider && (
        <>
          <div className="mb-6 mt-3">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{provider.name}</h1>
              <Badge>{ASSET_CLASS_LABELS[provider.asset_class]}</Badge>
            </div>
            <p className="mt-2 max-w-3xl text-sm text-slate-500">{provider.description}</p>
            <p className="mt-2 text-xs text-slate-400">
              {provider.hq}
              {provider.founded_year ? ` · est. ${provider.founded_year}` : ''}
              {provider.aum_busd ? ` · AUM ${fmtSize(provider.aum_busd * 1000)}` : ''}
            </p>
          </div>
          <Card>
            <CardContent className="p-0">
              <FundTable funds={provider.funds} />
            </CardContent>
          </Card>
        </>
      )}
    </Shell>
  )
}
