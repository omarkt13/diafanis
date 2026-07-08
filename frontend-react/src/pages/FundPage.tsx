import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { ConfidenceBadge } from '@/components/badges'
import { Shell } from '@/components/Shell'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { fmtMultiple, fmtPct, fmtSignedPct, fmtSize, fmtStatus } from '@/lib/format'
import { getFund, getFundSeries, keys } from '@/lib/queries'
import { ASSET_CLASS_LABELS } from '@/lib/types'

function MetricCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{label}</p>
        <p className="mt-1 text-xl font-semibold tabular-nums">{value}</p>
        {hint && <p className="mt-0.5 text-xs text-slate-400">{hint}</p>}
      </CardContent>
    </Card>
  )
}

export function FundPage() {
  const { id = '' } = useParams()
  const fundId = Number(id)

  const fundQuery = useQuery({ queryKey: keys.fund(fundId), queryFn: () => getFund(fundId) })
  const seriesQuery = useQuery({ queryKey: keys.series(fundId), queryFn: () => getFundSeries(fundId) })

  const fund = fundQuery.data
  const metrics = fund?.metrics ?? null
  const series =
    seriesQuery.data?.map((p) => ({
      date: p.period_date.slice(0, 7),
      'Est. TVPI': p.est_tvpi,
      'Benchmark (PME)': p.benchmark_tvpi,
    })) ?? []

  return (
    <Shell>
      {fund && (
        <Link to={`/providers/${fund.provider_slug}`} className="text-sm text-slate-500 hover:underline">
          ← {fund.provider_name}
        </Link>
      )}
      {fundQuery.isLoading && <p className="mt-4 text-sm text-slate-500">Loading…</p>}
      {fund && (
        <>
          <div className="mb-6 mt-3">
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight">{fund.name}</h1>
              <Badge>{ASSET_CLASS_LABELS[fund.asset_class]}</Badge>
              <ConfidenceBadge value={metrics?.confidence ?? null} />
            </div>
            <p className="mt-2 text-sm text-slate-500">
              {fund.provider_name} · vintage {fund.vintage_year} · {fmtSize(fund.fund_size_musd)} ·{' '}
              {fmtStatus(fund.status)}
              {fund.strategy ? ` · ${fund.strategy}` : ''}
            </p>
          </div>

          {metrics ? (
            <>
              <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                <MetricCard label="Est. TVPI / MOIC" value={fmtMultiple(metrics.est_tvpi)} />
                <MetricCard label="Est. DPI" value={fmtMultiple(metrics.est_dpi)} hint="realized" />
                <MetricCard label="Est. RVPI" value={fmtMultiple(metrics.est_rvpi)} hint="unrealized" />
                <MetricCard label="Est. NAV" value={fmtSize(metrics.est_nav_musd)} />
                <MetricCard label="Est. Net IRR" value={fmtPct(metrics.est_net_irr)} />
                <MetricCard
                  label="PME Alpha"
                  value={fmtSignedPct(metrics.pme_alpha)}
                  hint="vs blended benchmark"
                />
              </div>

              {metrics.narrative && (
                <Card className="mb-6">
                  <CardContent className="p-5">
                    <p className="text-sm leading-relaxed text-slate-700">{metrics.narrative}</p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <p className="mb-6 text-sm text-slate-500">
              Valuation is being computed — check back shortly.
            </p>
          )}

          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Estimate of value over time</CardTitle>
              <p className="text-sm text-slate-500">
                Modeled net TVPI vs. the same cashflows invested in the fund's blended public
                benchmark.
              </p>
            </CardHeader>
            <CardContent>
              {series.length > 0 ? (
                <div className="h-72 w-full">
                  <ResponsiveContainer>
                    <LineChart data={series} margin={{ top: 4, right: 12, bottom: 4, left: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                      <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickFormatter={(v: number) => `${v.toFixed(1)}x`}
                        domain={['auto', 'auto']}
                      />
                      <Tooltip formatter={(v: unknown) => (typeof v === 'number' ? `${v.toFixed(2)}x` : String(v ?? ''))} />
                      <Legend />
                      <Line type="monotone" dataKey="Est. TVPI" stroke="#0f172a" dot={false} strokeWidth={2} />
                      <Line
                        type="monotone"
                        dataKey="Benchmark (PME)"
                        stroke="#94a3b8"
                        dot={false}
                        strokeWidth={2}
                        strokeDasharray="6 4"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <p className="text-sm text-slate-500">Series not available yet.</p>
              )}
            </CardContent>
          </Card>

          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Benchmark breakdown</CardTitle>
              <p className="text-sm text-slate-500">
                The public comps that drive this fund's beta, weighted by its sector exposure.
              </p>
            </CardHeader>
            <CardContent className="flex flex-col gap-5">
              {fund.exposures.map((exposure) => (
                <div key={exposure.sector_tag}>
                  <p className="mb-2 text-sm font-medium">
                    {exposure.basket_name}{' '}
                    <span className="font-normal text-slate-400">
                      · {fmtPct(exposure.weight, 0)} of exposure
                    </span>
                  </p>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Ticker</TableHead>
                        <TableHead>Basket weight</TableHead>
                        <TableHead>Trailing 1y return</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {exposure.constituents.map((c) => (
                        <TableRow key={c.ticker}>
                          <TableCell className="font-medium">{c.ticker}</TableCell>
                          <TableCell>{fmtPct(c.weight, 0)}</TableCell>
                          <TableCell>
                            <span
                              className={
                                c.trailing_return_1y == null
                                  ? ''
                                  : c.trailing_return_1y >= 0
                                    ? 'text-emerald-700'
                                    : 'text-rose-700'
                              }
                            >
                              {fmtSignedPct(c.trailing_return_1y)}
                            </span>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              ))}
              {fund.macro.length > 0 && (
                <p className="text-xs text-slate-400">
                  Macro context: {fund.macro.map((m) => `${m.label}: ${m.value}`).join(' · ')}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Methodology & sources</CardTitle>
            </CardHeader>
            <CardContent className="text-sm leading-relaxed text-slate-600">
              <p>
                Estimates come from a quarterly pacing model: contributions drawn over the
                investment period, deployed capital compounded at the blended benchmark return
                (scaled for asset-class leverage), exit pacing from mid-life, and 2/20 fees over
                an 8% pref — all net-of-fee.{' '}
                {fund.reported_tvpi ? (
                  <>
                    This fund has a public reported mark of {fmtMultiple(fund.reported_tvpi)} as of{' '}
                    {fund.reported_as_of} ({fund.reported_source}); the model is calibrated to pass
                    through that mark and rolled forward on benchmark returns since.
                  </>
                ) : (
                  <>No public mark is available for this fund, so the estimate is model-only.</>
                )}{' '}
                PME alpha is Kaplan-Schoar: cash-weighted performance vs. the blended benchmark.
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </Shell>
  )
}
