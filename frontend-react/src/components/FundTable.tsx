import { Link } from 'react-router-dom'

import { PmeBadge } from '@/components/badges'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { fmtMultiple, fmtPct, fmtSize, fmtStatus } from '@/lib/format'
import type { FundListItem } from '@/lib/types'

export function FundTable({ funds, showProvider = false }: { funds: FundListItem[]; showProvider?: boolean }) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Fund</TableHead>
          {showProvider && <TableHead>Provider</TableHead>}
          <TableHead>Vintage</TableHead>
          <TableHead>Size</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Est. TVPI</TableHead>
          <TableHead>Est. Net IRR</TableHead>
          <TableHead>PME α</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {funds.map((fund) => (
          <TableRow key={fund.id}>
            <TableCell>
              <Link to={`/funds/${fund.id}`} className="font-medium text-slate-900 hover:underline">
                {fund.name}
              </Link>
            </TableCell>
            {showProvider && (
              <TableCell>
                <Link to={`/providers/${fund.provider_slug}`} className="text-slate-600 hover:underline">
                  {fund.provider_name}
                </Link>
              </TableCell>
            )}
            <TableCell>{fund.vintage_year}</TableCell>
            <TableCell>{fmtSize(fund.fund_size_musd)}</TableCell>
            <TableCell className="text-slate-500">{fmtStatus(fund.status)}</TableCell>
            <TableCell className="font-medium">{fmtMultiple(fund.est_tvpi)}</TableCell>
            <TableCell>{fmtPct(fund.est_net_irr)}</TableCell>
            <TableCell>
              <PmeBadge value={fund.pme_alpha} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
